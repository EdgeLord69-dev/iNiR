pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import Quickshell
import Quickshell.Io
import qs.modules.common
import qs.services

/**
 * VPN state from the two places a desktop actually keeps it: NetworkManager
 * connection profiles (OpenVPN, WireGuard, IPSec, anything with an NM plugin)
 * and Tailscale, which runs beside NetworkManager rather than inside it.
 *
 * There is no background polling: refreshes follow nmcli monitor through
 * Network.networkChanged and callers asking; a timer runs only while a surface holds
 * the service alive, because Tailscale changes do not reach NetworkManager.
 */
Singleton {
    id: root

    property var profiles: []
    property bool tailscaleInstalled: false
    property string tailscaleState: ""
    property string tailscaleHost: ""
    property string tailscaleAddress: ""
    property int tailscalePeers: 0
    property string tailscaleExitNode: ""
    property string lastError: ""
    property bool busy: false

    readonly property bool needsTailscaleOperator: /access denied|operator/i.test(root.lastError)
    readonly property bool needsSecrets: /secret|password|no valid.*key/i.test(root.lastError)
    readonly property string errorText: {
        if (root.lastError.length === 0) return ""
        if (root.needsTailscaleOperator)
            return Translation.tr("Tailscale only takes orders from root until your user is its operator.")
        if (root.needsSecrets)
            return Translation.tr("This profile needs its password stored in NetworkManager to connect from here.")
        return root.lastError
    }
    function fixTailscaleOperator(): void {
        root.busy = true
        root.lastError = ""
        actionProc.exec(["pkexec", "tailscale", "set", "--operator=" + Quickshell.env("USER")])
    }

    readonly property bool tailscaleUp: root.tailscaleState === "Running"
    readonly property var activeProfiles: root.profiles.filter(entry => entry.active)
    readonly property bool connected: root.activeProfiles.length > 0 || root.tailscaleUp
    readonly property int activeCount: root.activeProfiles.length + (root.tailscaleUp ? 1 : 0)
    readonly property bool available: root.profiles.length > 0 || root.tailscaleInstalled
    readonly property string activeName: root.activeProfiles[0]?.name
        ?? (root.tailscaleUp ? "Tailscale" : "")

    property int watchers: 0
    function keepAlive(): void { root.watchers += 1; root.refresh() }
    function releaseKeepAlive(): void { root.watchers = Math.max(0, root.watchers - 1) }

    function refresh(): void {
        profilesProc.running = true
        tailscaleProc.running = true
    }

    function setProfile(uuid: string, up: bool): void {
        if (String(uuid ?? "").length === 0) return
        root.busy = true
        root.lastError = ""
        actionProc.exec(["nmcli", "connection", up ? "up" : "down", "uuid", uuid])
    }
    function toggleProfile(uuid: string): void {
        const entry = root.profiles.find(item => item.uuid === uuid)
        if (!entry) return
        root.setProfile(uuid, !entry.active)
    }
    function setTailscale(up: bool): void {
        if (!root.tailscaleInstalled) return
        root.busy = true
        root.lastError = ""
        actionProc.exec(["tailscale", up ? "up" : "down"])
    }
    function toggleTailscale(): void { root.setTailscale(!root.tailscaleUp) }
    function toggle(): void {
        if (root.connected) {
            root.busy = true
            root.lastError = ""
            // One process for every profile: a second exec on the same Process would cut the first short.
            actionProc.exec(["bash", "-c", 'status=0; [ "$1" = 1 ] && { tailscale down || status=$?; }; shift; '
                + 'for uuid in "$@"; do nmcli connection down uuid "$uuid" || status=$?; done; exit $status',
                "_", root.tailscaleUp ? "1" : "0", ...root.activeProfiles.map(entry => entry.uuid)])
            return
        }
        if (root.tailscaleInstalled) { root.setTailscale(true); return }
        const first = root.profiles[0]
        if (first) root.setProfile(first.uuid, true)
    }

    Connections {
        target: Network
        function onNetworkChanged(): void { root.refresh() }
    }

    Timer {
        interval: 10000
        repeat: true
        running: root.watchers > 0
        onTriggered: root.refresh()
    }

    Component.onCompleted: root.refresh()

    Process {
        id: profilesProc
        running: false
        command: ["nmcli", "-t", "-f", "NAME,UUID,TYPE,ACTIVE", "connection", "show"]
        stdout: StdioCollector {
            onStreamFinished: {
                const found = []
                for (const line of text.split("\n")) {
                    if (line.trim().length === 0) continue
                    // nmcli -t escapes colons inside fields as "\:"
                    const parts = line.replace(/\\:/g, "\u0000").split(":").map(part => part.replace(/\u0000/g, ":"))
                    if (parts.length < 4) continue
                    const type = parts[2]
                    if (type !== "vpn" && type !== "wireguard") continue
                    found.push({
                        name: parts[0],
                        uuid: parts[1],
                        type: type === "wireguard" ? "WireGuard" : "VPN",
                        active: parts[3] === "yes"
                    })
                }
                root.profiles = found
            }
        }
    }

    Process {
        id: tailscaleProc
        running: false
        command: ["tailscale", "status", "--json"]
        stdout: StdioCollector {
            onStreamFinished: {
                if (text.trim().length === 0) return
                try {
                    const data = JSON.parse(text)
                    root.tailscaleInstalled = true
                    root.tailscaleState = String(data.BackendState ?? "")
                    root.tailscaleHost = String(data.Self?.HostName ?? "")
                    root.tailscaleAddress = String((data.Self?.TailscaleIPs ?? [])[0] ?? "")
                    root.tailscalePeers = Object.keys(data.Peer ?? {}).length
                    root.tailscaleExitNode = String(data.ExitNodeStatus?.ID ?? "")
                } catch (error) {
                    root.tailscaleInstalled = false
                }
            }
        }
        onExited: exitCode => { if (exitCode !== 0 && exitCode !== 1) root.tailscaleInstalled = false }
    }

    Process {
        id: actionProc
        running: false
        stderr: StdioCollector {
            onStreamFinished: root.lastError = text.trim().split("\n")[0] ?? ""
        }
        onExited: {
            root.busy = false
            root.refresh()
        }
    }
}
