import Foundation

struct CapturedMIDIEvent: Codable {
    let type: String
    let tick: Int
    let duration: Int?
    let channel: Int?
    let pitch: Int?
    let velocity: Int?
}

struct BridgeIngestPayload: Codable {
    let instance_id: String
    let track_name: String
    let source: String
    let events: [CapturedMIDIEvent]
}

final class LogicProMCPBridgeClient {
    private let endpoint = URL(string: "http://127.0.0.1:8765/ingest")!
    private let instanceID: String
    private var trackName: String

    init(instanceID: String = UUID().uuidString, trackName: String = "Logic Track") {
        self.instanceID = instanceID
        self.trackName = trackName
    }

    func updateTrackName(_ name: String) {
        trackName = name
    }

    func send(events: [CapturedMIDIEvent]) {
        guard !events.isEmpty else {
            return
        }

        let payload = BridgeIngestPayload(
            instance_id: instanceID,
            track_name: trackName,
            source: "logic-auv3",
            events: events
        )

        var request = URLRequest(url: endpoint)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try? JSONEncoder().encode(payload)

        URLSession.shared.dataTask(with: request).resume()
    }
}

// This file is a protocol sketch, not a complete AUv3 implementation.
// The AUv3 audio unit should call LogicProMCPBridgeClient.send(events:)
// from a non-realtime context after copying MIDI data out of the render path.
