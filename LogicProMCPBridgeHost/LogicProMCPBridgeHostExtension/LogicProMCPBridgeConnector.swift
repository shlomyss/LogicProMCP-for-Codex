import Foundation

public struct CapturedMIDIEvent: Codable, Equatable {
    public let type: String
    public let tick: Int
    public let duration: Int?
    public let channel: Int?
    public let pitch: Int?
    public let velocity: Int?
    public let controller: Int?
    public let value: Int?

    public init(
        type: String,
        tick: Int,
        duration: Int? = nil,
        channel: Int? = nil,
        pitch: Int? = nil,
        velocity: Int? = nil,
        controller: Int? = nil,
        value: Int? = nil
    ) {
        self.type = type
        self.tick = tick
        self.duration = duration
        self.channel = channel
        self.pitch = pitch
        self.velocity = velocity
        self.controller = controller
        self.value = value
    }
}

public struct LogicProMCPBridgeConfiguration {
    public let endpoint: URL
    public let source: String
    public let flushInterval: TimeInterval
    public let maxBatchSize: Int
    public let maxBufferedEvents: Int
    public let requestTimeout: TimeInterval

    public init(
        endpoint: URL = URL(string: "http://127.0.0.1:8765")!,
        source: String = "logic-auv3",
        flushInterval: TimeInterval = 0.5,
        maxBatchSize: Int = 512,
        maxBufferedEvents: Int = 8192,
        requestTimeout: TimeInterval = 2.0
    ) {
        self.endpoint = endpoint
        self.source = source
        self.flushInterval = flushInterval
        self.maxBatchSize = max(1, maxBatchSize)
        self.maxBufferedEvents = max(1, maxBufferedEvents)
        self.requestTimeout = requestTimeout
    }
}

public struct BridgeIngestPayload: Codable {
    public let instanceID: String
    public let trackName: String
    public let source: String
    public let events: [CapturedMIDIEvent]

    enum CodingKeys: String, CodingKey {
        case instanceID = "instance_id"
        case trackName = "track_name"
        case source
        case events
    }
}

public struct BridgeIngestResponse: Codable, Equatable {
    public let ok: Bool
    public let instanceID: String?
    public let trackName: String?
    public let acceptedEvents: Int?
    public let error: String?

    enum CodingKeys: String, CodingKey {
        case ok
        case instanceID = "instance_id"
        case trackName = "track_name"
        case acceptedEvents = "accepted_events"
        case error
    }
}

public struct BridgeHealthResponse: Codable, Equatable {
    public let ok: Bool
    public let service: String?
}

public enum LogicProMCPBridgeError: Error, LocalizedError {
    case invalidResponse
    case serverRejected(String)

    public var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "LogicProMCP bridge returned an invalid HTTP response."
        case .serverRejected(let message):
            return "LogicProMCP bridge rejected the request: \(message)"
        }
    }
}

public final class LogicProMCPBridgeConnector {
    private let configuration: LogicProMCPBridgeConfiguration
    private let instanceID: String
    private let session: URLSession
    private let networkQueue = DispatchQueue(label: "LogicProMCPBridgeConnector.network")
    private let lock = NSLock()
    private var trackName: String
    private var buffer: [CapturedMIDIEvent] = []
    private var timer: DispatchSourceTimer?
    private var isStarted = false
    private var isFlushInFlight = false

    public init(
        instanceID: String = UUID().uuidString,
        trackName: String = "Logic Track",
        configuration: LogicProMCPBridgeConfiguration = LogicProMCPBridgeConfiguration()
    ) {
        self.instanceID = instanceID
        self.trackName = trackName
        self.configuration = configuration

        let sessionConfiguration = URLSessionConfiguration.ephemeral
        sessionConfiguration.timeoutIntervalForRequest = configuration.requestTimeout
        sessionConfiguration.timeoutIntervalForResource = configuration.requestTimeout
        self.session = URLSession(configuration: sessionConfiguration)
    }

    deinit {
        stop(flushPending: false)
    }

    public func start() {
        lock.lock()
        defer { lock.unlock() }

        guard !isStarted else {
            return
        }

        let timer = DispatchSource.makeTimerSource(queue: networkQueue)
        timer.schedule(
            deadline: .now() + configuration.flushInterval,
            repeating: configuration.flushInterval
        )
        timer.setEventHandler { [weak self] in
            self?.flush()
        }
        timer.resume()
        self.timer = timer
        isStarted = true
    }

    public func stop(flushPending: Bool = true) {
        lock.lock()
        let timer = self.timer
        self.timer = nil
        isStarted = false
        lock.unlock()

        timer?.cancel()

        if flushPending {
            flush()
        }
    }

    public func updateTrackName(_ name: String) {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        lock.lock()
        trackName = trimmed.isEmpty ? "Logic Track" : trimmed
        lock.unlock()
    }

    public func capture(event: CapturedMIDIEvent) {
        capture(events: [event])
    }

    public func capture(events: [CapturedMIDIEvent]) {
        guard !events.isEmpty else {
            return
        }

        lock.lock()
        buffer.append(contentsOf: events)
        if buffer.count > configuration.maxBufferedEvents {
            buffer.removeFirst(buffer.count - configuration.maxBufferedEvents)
        }
        lock.unlock()
    }

    public func flush(completion: ((Result<BridgeIngestResponse, Error>) -> Void)? = nil) {
        let payload = nextPayload()
        guard let payload else {
            completion?(.success(BridgeIngestResponse(
                ok: true,
                instanceID: instanceID,
                trackName: currentTrackName(),
                acceptedEvents: 0,
                error: nil
            )))
            return
        }

        post(payload: payload) { [weak self] result in
            if case .failure = result {
                self?.finishFlush(restoring: payload.events)
            } else {
                self?.finishFlush(restoring: [])
            }
            completion?(result)
        }
    }

    public func health(completion: @escaping (Result<BridgeHealthResponse, Error>) -> Void) {
        request(path: "/health", method: "GET", body: Optional<Data>.none, completion: completion)
    }

    public func resetBridge(completion: @escaping (Result<BridgeHealthResponse, Error>) -> Void) {
        request(path: "/reset", method: "POST", body: Optional<Data>.none, completion: completion)
    }

    private func nextPayload() -> BridgeIngestPayload? {
        lock.lock()
        defer { lock.unlock() }

        guard !isFlushInFlight, !buffer.isEmpty else {
            return nil
        }

        let count = min(configuration.maxBatchSize, buffer.count)
        let events = Array(buffer.prefix(count))
        buffer.removeFirst(count)
        isFlushInFlight = true

        return BridgeIngestPayload(
            instanceID: instanceID,
            trackName: trackName,
            source: configuration.source,
            events: events
        )
    }

    private func currentTrackName() -> String {
        lock.lock()
        defer { lock.unlock() }
        return trackName
    }

    private func finishFlush(restoring events: [CapturedMIDIEvent]) {
        lock.lock()
        if !events.isEmpty {
            buffer.insert(contentsOf: events, at: 0)
            if buffer.count > configuration.maxBufferedEvents {
                buffer.removeLast(buffer.count - configuration.maxBufferedEvents)
            }
        }
        isFlushInFlight = false
        lock.unlock()
    }

    private func post(
        payload: BridgeIngestPayload,
        completion: @escaping (Result<BridgeIngestResponse, Error>) -> Void
    ) {
        do {
            let body = try JSONEncoder().encode(payload)
            request(path: "/ingest", method: "POST", body: body, completion: completion)
        } catch {
            completion(.failure(error))
        }
    }

    private func request<Response: Decodable>(
        path: String,
        method: String,
        body: Data?,
        completion: @escaping (Result<Response, Error>) -> Void
    ) {
        let normalizedPath = path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        var request = URLRequest(url: configuration.endpoint.appendingPathComponent(normalizedPath))
        request.httpMethod = method
        request.httpBody = body
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if body != nil {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        session.dataTask(with: request) { data, response, error in
            if let error {
                completion(.failure(error))
                return
            }

            guard let httpResponse = response as? HTTPURLResponse,
                  let data else {
                completion(.failure(LogicProMCPBridgeError.invalidResponse))
                return
            }

            do {
                let decoded = try JSONDecoder().decode(Response.self, from: data)
                if !(200...299).contains(httpResponse.statusCode) {
                    let message = String(data: data, encoding: .utf8) ?? "HTTP \(httpResponse.statusCode)"
                    completion(.failure(LogicProMCPBridgeError.serverRejected(message)))
                    return
                }
                completion(.success(decoded))
            } catch {
                completion(.failure(error))
            }
        }.resume()
    }
}

public struct MIDIMessageTranslator {
    private struct ActiveNoteKey: Hashable {
        let channel: Int
        let pitch: Int
    }

    private struct ActiveNote {
        let tick: Int
        let velocity: Int
    }

    private var activeNotes: [ActiveNoteKey: [ActiveNote]] = [:]

    public init() {}

    public mutating func consume(status: UInt8, data1: UInt8, data2: UInt8, tick: Int) -> CapturedMIDIEvent? {
        let statusType = status & 0xF0
        let channel = Int(status & 0x0F) + 1

        switch statusType {
        case 0x80:
            return closeNote(channel: channel, pitch: Int(data1), tick: tick)
        case 0x90:
            let velocity = Int(data2)
            if velocity == 0 {
                return closeNote(channel: channel, pitch: Int(data1), tick: tick)
            }
            let key = ActiveNoteKey(channel: channel, pitch: Int(data1))
            activeNotes[key, default: []].append(ActiveNote(
                tick: tick,
                velocity: velocity
            ))
            return nil
        case 0xB0:
            return CapturedMIDIEvent(
                type: "control_change",
                tick: tick,
                channel: channel,
                controller: Int(data1),
                value: Int(data2)
            )
        default:
            return CapturedMIDIEvent(
                type: "midi",
                tick: tick,
                channel: channel,
                controller: Int(statusType >> 4),
                value: Int(data1)
            )
        }
    }

    public mutating func consume(bytes: [UInt8], tick: Int) -> CapturedMIDIEvent? {
        guard bytes.count >= 3 else {
            return nil
        }
        return consume(status: bytes[0], data1: bytes[1], data2: bytes[2], tick: tick)
    }

    public mutating func flushOpenNotes(at tick: Int) -> [CapturedMIDIEvent] {
        let events = activeNotes.flatMap { key, notes in
            notes.map { note in
                CapturedMIDIEvent(
                    type: "note",
                    tick: note.tick,
                    duration: max(0, tick - note.tick),
                    channel: key.channel,
                    pitch: key.pitch,
                    velocity: note.velocity
                )
            }
        }
        activeNotes.removeAll()
        return events.sorted { lhs, rhs in
            if lhs.tick == rhs.tick {
                return (lhs.pitch ?? 0) < (rhs.pitch ?? 0)
            }
            return lhs.tick < rhs.tick
        }
    }

    private mutating func closeNote(channel: Int, pitch: Int, tick: Int) -> CapturedMIDIEvent? {
        let key = ActiveNoteKey(channel: channel, pitch: pitch)
        guard var notes = activeNotes[key], !notes.isEmpty else {
            return nil
        }
        let note = notes.removeFirst()
        activeNotes[key] = notes.isEmpty ? nil : notes

        return CapturedMIDIEvent(
            type: "note",
            tick: note.tick,
            duration: max(0, tick - note.tick),
            channel: channel,
            pitch: pitch,
            velocity: note.velocity
        )
    }
}

public final class LogicProMCPMIDIEventSink {
    private let connector: LogicProMCPBridgeConnector
    private var translator = MIDIMessageTranslator()

    public init(connector: LogicProMCPBridgeConnector) {
        self.connector = connector
    }

    public func consume(status: UInt8, data1: UInt8, data2: UInt8, tick: Int) {
        if let event = translator.consume(status: status, data1: data1, data2: data2, tick: tick) {
            connector.capture(event: event)
        }
    }

    public func consume(bytes: [UInt8], tick: Int) {
        if let event = translator.consume(bytes: bytes, tick: tick) {
            connector.capture(event: event)
        }
    }

    public func flushOpenNotes(at tick: Int) {
        connector.capture(events: translator.flushOpenNotes(at: tick))
    }
}

/*
 AUv3 integration outline:

 let connector = LogicProMCPBridgeConnector(trackName: "Bass")
 let sink = LogicProMCPMIDIEventSink(connector: connector)

 connector.start()

 // From the AU render path, copy incoming MIDI packets into a small lock-free
 // queue owned by the audio unit. From a non-realtime worker, translate them:
 sink.consume(status: statusByte, data1: noteByte, data2: velocityByte, tick: hostTick)

 // When playback stops or the extension is deallocated:
 sink.flushOpenNotes(at: currentHostTick)
 connector.stop()
 */
