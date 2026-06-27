//
//  Parameters.swift
//  LogicProMCPBridgeHostExtension
//
//  Created by Shlomy Sasson on 27/06/2026.
//

import Foundation
import AudioToolbox

let LogicProMCPBridgeHostExtensionParameterSpecs = ParameterTreeSpec {
    ParameterGroupSpec(identifier: "global", name: "Global") {
        ParameterSpec(
            address: .sendNote,
            identifier: "sendNote",
            name: "Send Note",
            units: .boolean,
            valueRange: 0...1,
            defaultValue: 0
        )
        
        ParameterSpec(
            address: .midiNoteNumber,
            identifier: "midiNoteNumber",
            name: "MIDI Note Number",
            units: .midiNoteNumber,
            valueRange: 0...127,
            defaultValue: 60,
            flags: [.flag_IsWritable] // so that hosts like AUM expose this as automatable
        )
    }
}

extension ParameterSpec {
    init(
        address: LogicProMCPBridgeHostExtensionParameterAddress,
        identifier: String,
        name: String,
        units: AudioUnitParameterUnit,
        valueRange: ClosedRange<AUValue>,
        defaultValue: AUValue,
        unitName: String? = nil,
        flags: AudioUnitParameterOptions = [AudioUnitParameterOptions.flag_IsWritable, AudioUnitParameterOptions.flag_IsReadable],
        valueStrings: [String]? = nil,
        dependentParameters: [NSNumber]? = nil
    ) {
        self.init(address: address.rawValue,
                  identifier: identifier,
                  name: name,
                  units: units,
                  valueRange: valueRange,
                  defaultValue: defaultValue,
                  unitName: unitName,
                  flags: flags,
                  valueStrings: valueStrings,
                  dependentParameters: dependentParameters)
    }
}
