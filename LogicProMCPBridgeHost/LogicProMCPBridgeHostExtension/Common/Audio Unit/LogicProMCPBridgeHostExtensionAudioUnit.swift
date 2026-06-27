//
//  LogicProMCPBridgeHostExtensionAudioUnit.swift
//  LogicProMCPBridgeHostExtension
//
//  Created by Shlomy Sasson on 27/06/2026.
//

import AVFoundation

public class LogicProMCPBridgeHostExtensionAudioUnit: AUAudioUnit, @unchecked Sendable
{
	// C++ Objects
	var kernel = LogicProMCPBridgeHostExtensionDSPKernel()
    var processHelper: AUProcessHelper?

	private var outputBus: AUAudioUnitBus?
	private var _outputBusses: AUAudioUnitBusArray!

	private var format:AVAudioFormat

	@objc override init(componentDescription: AudioComponentDescription, options: AudioComponentInstantiationOptions) throws {
		self.format = AVAudioFormat(standardFormatWithSampleRate: 44_100, channels: 2)!
		try super.init(componentDescription: componentDescription, options: options)
		outputBus = try AUAudioUnitBus(format: self.format)
        outputBus?.maximumChannelCount = 2
		_outputBusses = AUAudioUnitBusArray(audioUnit: self, busType: AUAudioUnitBusType.output, busses: [outputBus!])
        kernel.initialize(outputBus!.format.sampleRate)
        processHelper = AUProcessHelper(&kernel)
	}

	public override var outputBusses: AUAudioUnitBusArray {
		return _outputBusses
	}
    
    public override var  maximumFramesToRender: AUAudioFrameCount {
        get {
            return kernel.maximumFramesToRender()
        }

        set {
            kernel.setMaximumFramesToRender(newValue)
        }
    }

    public override var  shouldBypassEffect: Bool {
        get {
            return kernel.isBypassed()
        }

        set {
            kernel.setBypass(newValue)
        }
    }

    // MARK: - MIDI
    public override var audioUnitMIDIProtocol: MIDIProtocolID {
        return kernel.AudioUnitMIDIProtocol()
    }

    // MARK: - Rendering
    public override var internalRenderBlock: AUInternalRenderBlock {
        guard processHelper != nil else {
            return { _, _, _, _, _, _, _ in kAudioUnitErr_Uninitialized }
        }
        return processHelper!.internalRenderBlock()
    }

    // Allocate resources required to render.
    // Subclassers should call the superclass implementation.
    public override func allocateRenderResources() throws {
        guard let outputBus else {
            throw NSError(domain: NSOSStatusErrorDomain, code: Int(kAudioUnitErr_Uninitialized))
        }

        kernel.initialize(outputBus.format.sampleRate)
        try super.allocateRenderResources()
    }

    // Deallocate resources allocated in allocateRenderResourcesAndReturnError:
    // Subclassers should call the superclass implementation.
    public override func deallocateRenderResources() {
        
        kernel.deInitialize()
        super.deallocateRenderResources()
    }

	public func setupParameterTree(_ parameterTree: AUParameterTree) {
		self.parameterTree = parameterTree

		// Set the Parameter default values before setting up the parameter callbacks
		for param in parameterTree.allParameters {
            kernel.setParameter(param.address, param.value)
		}

		setupParameterCallbacks()
	}

	private func setupParameterCallbacks() {
		// implementorValueObserver is called when a parameter changes value.
		parameterTree?.implementorValueObserver = { [weak self] param, value -> Void in
            self?.kernel.setParameter(param.address, value)
		}

		// implementorValueProvider is called when the value needs to be refreshed.
		parameterTree?.implementorValueProvider = { [weak self] param in
            guard let self else { return param.value }
            return self.kernel.getParameter(param.address)
		}

		// Keep this callback allocation-free and locale-independent for hosts that
		// query parameter strings during AU discovery/loading.
		parameterTree?.implementorStringFromValueCallback = { _, valuePtr in
			guard let value = valuePtr?.pointee else {
				return ""
			}
            let rounded = value.rounded()
            if rounded == value {
                return String(Int(rounded))
            }
            return String(value)
		}
	}
}
