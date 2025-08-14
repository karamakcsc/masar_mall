// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt


frappe.ui.form.on("Floor Unit", {
    setup: function (frm) {
        frm.set_query("floor", function () {
            if (!frm.doc.property) {
                frappe.msgprint(__('Please select a Property first.'));
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
    },

    property: function (frm) {
        frm.refresh_field("floor");
    }
});

