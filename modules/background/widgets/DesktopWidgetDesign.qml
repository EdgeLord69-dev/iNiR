pragma Singleton
pragma ComponentBehavior: Bound

import QtQuick
import qs.modules.common

QtObject {
    id: root

    // A composition overlays only presentation keys. Stored sizes, content and
    // individual styles return unchanged when the global choice is Individual.
    readonly property string family: Config.options?.panelFamily ?? "ii"
    readonly property string shared: Config.options?.background?.widgets?.design ?? "individual"
    readonly property string current: root.family === "iris" && (Config.options?.iris?.widgets?.design ?? "iris") === "iris"
        ? "iris" : root.shared === "individual" ? "material" : root.shared
    readonly property var choices: [
        { label: "Individual", value: "individual", icon: "widgets" },
        { label: "iNstrument", value: "instrument", icon: "avg_pace" },
        { label: "Readout", value: "readout", icon: "view_agenda" }
    ]
    readonly property var instruments: ({
        clock: { style: "instrument" }, weather: { style: "dial" },
        systemMonitor: { displayMode: "instrument" }, battery: { displayMode: "instrument" },
        dayProgress: { style: "ring" }, notes: { style: "instrument" },
        calendarUpcoming: { style: "instrument" }, monthCalendar: { style: "instrument" },
        todo: { style: "instrument" }, timers: { style: "instrument" },
        dateBadge: { style: "instrument" }, uptime: { style: "instrument" },
        worldClock: { style: "instrument" }, userCard: { style: "instrument" },
        newsTicker: { style: "instrument" }
    })
    readonly property var readouts: ({
        clock: { style: "digital" }, systemMonitor: { displayMode: "text", showBackground: false, showBorder: false },
        dayProgress: { style: "arc", comet: false, hourLabels: false },
        dateBadge: { style: "instrument", instrumentMarks: false },
        worldClock: { style: "instrument", instrumentLayout: "rows" },
        monthCalendar: { style: "instrument", instrumentRule: false },
        todo: { style: "instrument", instrumentRules: false }
    })

    function supports(widget: string): bool { return root.instruments[widget] !== undefined }
    function values(widget: string, design: string): var {
        if (design === "instrument") return root.instruments[widget] ?? ({})
        if (design === "readout") return root.readouts[widget] ?? root.instruments[widget] ?? ({})
        return ({})
    }
    function apply(design: string): string {
        if (!["iris", "material", "individual", "instrument", "readout"].includes(design))
            return "Choose iris, material, individual, instrument or readout"
        if (design === "iris" && root.family !== "iris") return "iRiS faces need the iRiS family"
        const updates = { "background.widgets.design": ["instrument", "readout"].includes(design) ? design : "individual" }
        if (root.family === "iris") updates["iris.widgets.design"] = design === "iris" ? "iris" : "material"
        Config.setNestedValues(updates)
        return design
    }
}
