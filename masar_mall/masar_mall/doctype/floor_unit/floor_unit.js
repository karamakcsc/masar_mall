// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt

frappe.ui.form.on("Floor Unit", {
    setup: function (frm) {
        filter_floor(frm);
    },
    property: function (frm) {
        frm.refresh_field("floor");
    },
    refresh: function(frm) {
        disable_button(frm)
    }
});

function filter_floor(frm) {
    frm.set_query("floor", function () {
        if (!frm.doc.property) {
            return { filters: { name: "" } };
        }
        return {
            filters: {
                property: frm.doc.property,
                disable: 0,
                docstatus: 1
            }
        };
    });
}

function disable_button(frm) {
    if (frm.doc.docstatus === 1 && frm.doc.disabled === 0) {
        frm.add_custom_button(__('Disable'), function() {
            frappe.confirm(
                __('Are you sure you want to disable this Floor Unit? This will reverse all stock entries.'),
                function() {
                    frappe.call({
                        doc: frm.doc,
                        method: "disable_unit",
                        callback: function(r) {
                            if (!r.exc) {
                                frm.reload_doc();
                                frappe.show_alert({
                                    message: __('Floor Unit disabled successfully'),
                                    indicator: 'green'
                                }, 5);
                            }
                        }
                    });
                }
            );
        }, __("Manage"));
    }
}