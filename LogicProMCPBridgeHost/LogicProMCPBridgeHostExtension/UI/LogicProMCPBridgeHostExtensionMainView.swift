//
//  LogicProMCPBridgeHostExtensionMainView.swift
//  LogicProMCPBridgeHostExtension
//
//  Created by Shlomy Sasson on 27/06/2026.
//

import SwiftUI

struct LogicProMCPBridgeHostExtensionMainView: View {
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(verbatim: "LogicProMCP")
                .font(.headline)
            Text(verbatim: "Bridge MIDI processor loaded")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .padding(16)
        .frame(minWidth: 280, minHeight: 120, alignment: .leading)
    }
}
