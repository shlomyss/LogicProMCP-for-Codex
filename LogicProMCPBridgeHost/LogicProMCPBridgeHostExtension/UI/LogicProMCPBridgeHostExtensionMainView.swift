//
//  LogicProMCPBridgeHostExtensionMainView.swift
//  LogicProMCPBridgeHostExtension
//
//  Created by Shlomy Sasson on 27/06/2026.
//

import SwiftUI

struct LogicProMCPBridgeHostExtensionMainView: View {
    var parameterTree: ObservableAUParameterGroup
    
    var body: some View {
        VStack {
            ParameterSlider(param: parameterTree.global.midiNoteNumber)
                .padding()
            MomentaryButton(
                "Play note",
                param: parameterTree.global.sendNote
            )
        }
    }
}
