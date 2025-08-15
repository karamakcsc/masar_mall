// Copyright (c) 2025, KCSC and contributors
// For license information, please see license.txt


frappe.ui.form.on("Unit Managment", {
    setup: function (frm) {
        frm.set_query("exit_floor_unit", function () {
            if (!frm.doc.property) {
                frappe.msgprint(__('Please select a Property first.'));
                return { filters: { name: "" } };
            }
            return {
                filters: {
                    property: frm.doc.property,
                    floor: frm.doc.floor,
                    disable: 0,
                    docstatus: 1,
                    return_space: 0,
                    rent_space: 1
                }
            };
        });
    },

    property: function (frm) {
        frm.refresh_field("exit_floor_unit");
    }
});
frappe.ui.form.on("Unit Managment", {
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
        frm.refresh_field("exit_floor_unit");
    }
});
