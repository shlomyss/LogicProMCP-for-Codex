//
//  LogicProMCPBridgeHostApp.swift
//  LogicProMCPBridgeHost
//
//  Created by Shlomy Sasson on 27/06/2026.
//

import SwiftUI

@main
struct LogicProMCPBridgeHostApp: App {
    private let hostModel = AudioUnitHostModel()

    var body: some Scene {
        WindowGroup {
            ContentView(hostModel: hostModel)
        }
    }
}
