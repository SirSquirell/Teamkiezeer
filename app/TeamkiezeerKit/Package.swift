// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TeamkiezeerKit",
    platforms: [.iOS(.v17), .macOS(.v14)],
    products: [
        .library(name: "TeamkiezeerKit", targets: ["TeamkiezeerKit"])
    ],
    targets: [
        .target(name: "TeamkiezeerKit"),
        .testTarget(name: "TeamkiezeerKitTests", dependencies: ["TeamkiezeerKit"])
    ]
)
