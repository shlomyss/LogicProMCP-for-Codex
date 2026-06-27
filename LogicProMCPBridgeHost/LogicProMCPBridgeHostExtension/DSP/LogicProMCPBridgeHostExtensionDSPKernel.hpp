//
//  LogicProMCPBridgeHostExtensionDSPKernel.hpp
//  LogicProMCPBridgeHostExtension
//
//  Created by Shlomy Sasson on 27/06/2026.
//

#pragma once

#import <AudioToolbox/AudioToolbox.h>
#import <CoreMIDI/MIDIMessages.h>

#import <algorithm>
#import <vector>

#import "LogicProMCPBridgeHostExtensionParameterAddresses.h"

constexpr uint16_t kMaxVelocity = std::numeric_limits<std::uint16_t>::max();

/*
 LogicProMCPBridgeHostExtensionDSPKernel
 As a non-ObjC class, this is safe to use from render thread.
 */
class LogicProMCPBridgeHostExtensionDSPKernel {
public:
    void initialize(double inSampleRate) {
        mSampleRate = inSampleRate;
    }
    
    void deInitialize() {
        mMIDIOutBlock = nullptr;
        mShouldSendNoteOn = false;
        mNoteIsCurrentlyOn = false;
    }
    
    // MARK: - Bypass
    bool isBypassed() {
        return mBypassed;
    }
    
    void setBypass(bool shouldBypass) {
        mBypassed = shouldBypass;
    }
    
    // MARK: - Parameter Getter / Setter
    // Add a case for each parameter in LogicProMCPBridgeHostExtensionParameterAddresses.h
    void setParameter(AUParameterAddress address, AUValue value) {
        switch (address) {
            case LogicProMCPBridgeHostExtensionParameterAddress::midiNoteNumber: {
                const auto clamped = std::clamp(value, AUValue(0), AUValue(127));
                mNextNoteToSend = static_cast<uint8_t>(clamped);
                break;
            }
            case LogicProMCPBridgeHostExtensionParameterAddress::sendNote:
                mShouldSendNoteOn = value >= 0.5f;
                break;
        }
    }
    
    AUValue getParameter(AUParameterAddress address) {
        // Return the goal. It is not thread safe to return the ramping value.
        
        switch (address) {
            case LogicProMCPBridgeHostExtensionParameterAddress::midiNoteNumber:
                return (AUValue)mNextNoteToSend;
                
            case LogicProMCPBridgeHostExtensionParameterAddress::sendNote:
                return mShouldSendNoteOn ? 1.f : 0.f;
                
            default: return 0.f;
        }
    }
    
    // MARK: - Maximum Frames To Render
    AUAudioFrameCount maximumFramesToRender() const {
        return mMaxFramesToRender;
    }
    
    void setMaximumFramesToRender(const AUAudioFrameCount &maxFrames) {
        mMaxFramesToRender = maxFrames;
    }
    
    // MARK: - MIDI Output
    void setMIDIOutputEventBlock(AUMIDIEventListBlock midiOutBlock) {
        mMIDIOutBlock = midiOutBlock;
    }
    
    // MARK: - MIDI Protocol
    MIDIProtocolID AudioUnitMIDIProtocol() const {
        return kMIDIProtocol_2_0;
    }
    
    /**
     MARK: - Internal Process
     
     This function does the core siginal processing.
     Do your custom MIDI processing here.
     */
    void process(AUEventSampleTime bufferStartTime, AUAudioFrameCount frameCount) {
        
        if (mBypassed) { return; }
        
        /*
         // If you require sample-accurate sequencing, calculate your midi events based on the frame and buffer offsets
         
         for (int frameIndex = 0; frameIndex < frameCount; ++frameIndex) {
         const int frameOffset = int(frameIndex + frameOffset);
         // Do sample-accurate sequencing here
         }
         */
        
        // Keep the baseline AU passive and side-effect free.

        
    }
    
    void sendNoteOn(AUEventSampleTime sampleTime, uint8_t noteNum, uint16_t velocity) {
        if (!mMIDIOutBlock) { return; }
        auto message = MIDI2NoteOn(0, 0, noteNum, 0, 0, velocity);
        MIDIEventList eventList = {};
        MIDIEventPacket *packet = MIDIEventListInit(&eventList, kMIDIProtocol_2_0);
        packet = MIDIEventListAdd(&eventList, sizeof(MIDIEventList), packet, 0, 2, (UInt32 *)&message);
        mMIDIOutBlock(sampleTime, 0, &eventList);
    }
    
    void sendNoteOff(AUEventSampleTime sampleTime, uint8_t noteNum, uint16_t velocity) {
        if (!mMIDIOutBlock) { return; }
        auto message = MIDI2NoteOff(0, 0, noteNum, 0, 0, velocity);
        MIDIEventList eventList = {};
        MIDIEventPacket *packet = MIDIEventListInit(&eventList, kMIDIProtocol_2_0);
        packet = MIDIEventListAdd(&eventList, sizeof(MIDIEventList), packet, 0, 2, (UInt32 *)&message);
        mMIDIOutBlock(sampleTime, 0, &eventList);
    }
    
    void handleOneEvent(AUEventSampleTime now, AURenderEvent const *event) {
        switch (event->head.eventType) {
            case AURenderEventParameter: {
                handleParameterEvent(now, event->parameter);
                break;
            }
                
            case AURenderEventMIDIEventList: {
                handleMIDIEventList(now, &event->MIDIEventsList);
                break;
            }
                
            default:
                break;
        }
    }

    void handleMIDIEventList(AUEventSampleTime now, AUMIDIEventList const* midiEvent) {
        /*
         // Parse UMP messages
         auto visitor = [] (void* context, MIDITimeStamp timeStamp, MIDIUniversalMessage message) {
         auto thisObject = static_cast<LogicProMCPBridgeHostExtensionDSPKernel *>(context);

         switch (message.type) {
         case kMIDIMessageTypeChannelVoice2: {
         }
         break;

         default:
         break;
         }
         };
         MIDIEventListForEachEvent(&midiEvent->eventList, visitor, this);
         */
        // MIDI forwarding will be added with the bridge capture path.
    }
    
    void handleParameterEvent(AUEventSampleTime now, AUParameterEvent const& parameterEvent) {
        setParameter(parameterEvent.parameterAddress, parameterEvent.value);
    }
    
    // MARK: Member Variables
    double mSampleRate = 44100.0;
    bool mBypassed = false;
    AUAudioFrameCount mMaxFramesToRender = 1024;
    
    bool mShouldSendNoteOn = false;  //  Should we send a note-on next process?
    bool mNoteIsCurrentlyOn = false;  //  Have we sent a note-on without a matching note off?
    uint8_t mLastSentNote = 255;
    uint8_t mNextNoteToSend = 60;
    AUMIDIEventListBlock mMIDIOutBlock = nullptr;
};
