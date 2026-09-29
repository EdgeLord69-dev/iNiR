import qs.modules.common
import "layouts.js" as Layouts
import QtQuick
import QtQuick.Layouts

Item {
    id: root    
    property var layouts: Layouts.byName
    property var activeLayoutName: (layouts.hasOwnProperty(Config.options?.osk.layout)) 
        ? Config.options?.osk.layout 
        : Layouts.defaultLayout
    property var currentLayout: layouts[activeLayoutName]
    // A family draws the keys its own way: it hands over a component with `required property var modelData`.
    property Component keyComponent: defaultKey
    property real keySpacing: 5

    Component {
        id: defaultKey
        OskKey {
            required property var modelData
            keyData: modelData
        }
    }

    implicitWidth: keyRows.implicitWidth
    implicitHeight: keyRows.implicitHeight

    ColumnLayout {
        id: keyRows
        anchors.fill: parent
        spacing: root.keySpacing

        Repeater {
            model: root.currentLayout.keys

            delegate: RowLayout {
                id: keyRow
                required property var modelData
                spacing: root.keySpacing
                
                Repeater {
                    model: modelData
                    // A normal key looks like this: {label: "a", labelShift: "A", shape: "normal", keycode: 30, type: "normal"}
                    delegate: root.keyComponent
                }
            }
        }
    }
}
