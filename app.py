"""
Awab Reselling Dashboard - Main Application
Personal reselling business tracking across multiple platforms
"""

import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from datetime import datetime, date
import csv
import io
from logger import get_logger
import db_supabase as db

# Load environment variables
load_dotenv()

# Get logger
logger = get_logger(__name__)

# Create Flask app
app = Flask(
    __name__,
    template_folder=os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "web_ui_plugin/templates"
    ),
    static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), "web_ui_plugin/static"),
)

# Secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))


@app.context_processor
def inject_app_info():
    """Inject app version and name into all templates"""
    settings = db.get_all_settings()
    return {
        'app_name': settings.get('app_name', 'Awab Reselling Dashboard'),
        'app_version': settings.get('app_version', '2.0.0'),
        'current_year': datetime.now().year
    }


# ============================
# DASHBOARD
# ============================

@app.route("/")
def index():
    """Main dashboard with KPIs and recent activity"""
    try:
        stats = db.get_dashboard_stats()
        recent_sales = db.get_sales(limit=5)
        recent_inventory = db.get_inventory(limit=8)
        pending_tasks = db.get_pending_tasks()[:5]

        return render_template(
            "dashboard.html",
            stats=stats,
            recent_sales=recent_sales,
            recent_inventory=recent_inventory,
            pending_tasks=pending_tasks
        )
    except Exception as e:
        logger.error(f"Error loading dashboard: {e}", exc_info=True)
        flash("Error loading dashboard", "danger")
        return render_template("dashboard.html", stats={}, recent_sales=[], recent_inventory=[], pending_tasks=[])


# ============================
# INVENTORY
# ============================

@app.route("/inventory")
def inventory():
    """Inventory management page"""
    status_filter = request.args.get("status", "")
    brand_filter = request.args.get("brand", "")
    limit = int(request.args.get("limit", 50))

    items = db.get_inventory(
        limit=limit,
        status=status_filter if status_filter else None,
        brand=brand_filter if brand_filter else None
    )

    # Get unique brands for filter
    all_items = db.get_inventory(limit=1000)
    brands = sorted(set(item.get('brand', '') for item in all_items if item.get('brand')))

    return render_template(
        "inventory.html",
        items=items,
        brands=brands,
        status_filter=status_filter,
        brand_filter=brand_filter,
        limit=limit
    )


@app.route("/inventory/add", methods=["GET", "POST"])
def add_inventory():
    """Add new inventory item"""
    if request.method == "POST":
        try:
            # Get form data
            platforms = request.form.getlist("platforms")

            item_data = {
                "sku": request.form.get("sku"),
                "item_name": request.form.get("item_name"),
                "category": request.form.get("category"),
                "size": request.form.get("size"),
                "condition": request.form.get("condition"),
                "brand": request.form.get("brand"),
                "platforms": platforms,
                "listing_status": request.form.get("listing_status", "Draft"),
                "purchase_price": float(request.form.get("purchase_price", 0)),
                "fees_estimate": float(request.form.get("fees_estimate", 0)),
                "shipping_paid_by": request.form.get("shipping_paid_by", "Buyer"),
                "shipping_cost": float(request.form.get("shipping_cost", 0)),
                "date_purchased": request.form.get("date_purchased") or None,
                "storage_location": request.form.get("storage_location"),
                "notes": request.form.get("notes"),
            }

            # Check if SKU already exists
            existing = db.get_inventory_by_sku(item_data["sku"])
            if existing:
                flash(f"SKU {item_data['sku']} already exists", "warning")
                return redirect(url_for("inventory"))

            result = db.add_inventory_item(item_data)
            if result:
                flash(f"Added {item_data['item_name']} to inventory", "success")
            else:
                flash("Error adding item", "danger")

            return redirect(url_for("inventory"))

        except Exception as e:
            logger.error(f"Error adding inventory: {e}", exc_info=True)
            flash("Error adding inventory item", "danger")
            return redirect(url_for("inventory"))

    return render_template("inventory_form.html", item=None, action="add")


@app.route("/inventory/edit/<item_id>", methods=["GET", "POST"])
def edit_inventory(item_id):
    """Edit inventory item"""
    if request.method == "POST":
        try:
            platforms = request.form.getlist("platforms")

            item_data = {
                "item_name": request.form.get("item_name"),
                "category": request.form.get("category"),
                "size": request.form.get("size"),
                "condition": request.form.get("condition"),
                "brand": request.form.get("brand"),
                "platforms": platforms,
                "listing_status": request.form.get("listing_status"),
                "purchase_price": float(request.form.get("purchase_price", 0)),
                "fees_estimate": float(request.form.get("fees_estimate", 0)),
                "shipping_paid_by": request.form.get("shipping_paid_by"),
                "shipping_cost": float(request.form.get("shipping_cost", 0)),
                "sale_price": float(request.form.get("sale_price")) if request.form.get("sale_price") else None,
                "date_purchased": request.form.get("date_purchased") or None,
                "date_listed": request.form.get("date_listed") or None,
                "date_sold": request.form.get("date_sold") or None,
                "storage_location": request.form.get("storage_location"),
                "notes": request.form.get("notes"),
            }

            # Calculate profit and ROI if sale_price exists
            if item_data["sale_price"]:
                item_data["profit"] = item_data["sale_price"] - item_data["purchase_price"] - item_data["fees_estimate"] - (item_data["shipping_cost"] if item_data["shipping_paid_by"] == "Seller" else 0)
                if item_data["purchase_price"] > 0:
                    item_data["roi_percent"] = (item_data["profit"] / item_data["purchase_price"]) * 100

            success = db.update_inventory_item(item_id, item_data)
            if success:
                flash("Inventory item updated", "success")
            else:
                flash("Error updating item", "danger")

            return redirect(url_for("inventory"))

        except Exception as e:
            logger.error(f"Error updating inventory: {e}", exc_info=True)
            flash("Error updating inventory item", "danger")
            return redirect(url_for("inventory"))

    item = db.get_inventory_by_id(item_id)
    if not item:
        flash("Item not found", "danger")
        return redirect(url_for("inventory"))

    return render_template("inventory_form.html", item=item, action="edit")


@app.route("/inventory/delete/<item_id>", methods=["POST"])
def delete_inventory(item_id):
    """Delete inventory item"""
    try:
        success = db.delete_inventory_item(item_id)
        if success:
            flash("Inventory item deleted", "success")
        else:
            flash("Error deleting item", "danger")
    except Exception as e:
        logger.error(f"Error deleting inventory: {e}", exc_info=True)
        flash("Error deleting inventory item", "danger")

    return redirect(url_for("inventory"))


# ============================
# SALES
# ============================

@app.route("/sales")
def sales():
    """Sales tracking page"""
    platform_filter = request.args.get("platform", "")
    limit = int(request.args.get("limit", 50))

    sales_data = db.get_sales(
        limit=limit,
        platform=platform_filter if platform_filter else None
    )

    # Calculate totals
    total_revenue = sum(float(sale.get('sale_price', 0)) for sale in sales_data)
    total_profit = sum(float(sale.get('net_profit', 0)) for sale in sales_data)

    return render_template(
        "sales.html",
        sales=sales_data,
        platform_filter=platform_filter,
        limit=limit,
        total_revenue=round(total_revenue, 2),
        total_profit=round(total_profit, 2)
    )


@app.route("/sales/add", methods=["GET", "POST"])
def add_sale():
    """Add new sale"""
    if request.method == "POST":
        try:
            sale_data = {
                "order_id": request.form.get("order_id"),
                "platform": request.form.get("platform"),
                "item_name": request.form.get("item_name"),
                "sale_price": float(request.form.get("sale_price")),
                "platform_fees": float(request.form.get("platform_fees", 0)),
                "payment_processing_fees": float(request.form.get("payment_processing_fees", 0)),
                "shipping_cost": float(request.form.get("shipping_cost", 0)),
                "buyer_paid_shipping": request.form.get("buyer_paid_shipping") == "on",
                "date_sold": request.form.get("date_sold"),
                "buyer_name": request.form.get("buyer_name"),
                "payout_status": request.form.get("payout_status", "Pending"),
                "notes": request.form.get("notes"),
            }

            # Calculate net profit
            shipping = sale_data["shipping_cost"] if not sale_data["buyer_paid_shipping"] else 0
            sale_data["net_profit"] = sale_data["sale_price"] - sale_data["platform_fees"] - sale_data["payment_processing_fees"] - shipping

            # Link to inventory if SKU provided
            inventory_sku = request.form.get("inventory_sku")
            if inventory_sku:
                inventory_item = db.get_inventory_by_sku(inventory_sku)
                if inventory_item:
                    sale_data["inventory_id"] = inventory_item["id"]

            result = db.add_sale(sale_data)
            if result:
                flash(f"Sale {sale_data['order_id']} added", "success")

                # Update inventory status if linked
                if sale_data.get("inventory_id"):
                    db.update_inventory_item(sale_data["inventory_id"], {
                        "listing_status": "Sold",
                        "date_sold": sale_data["date_sold"],
                        "sale_price": sale_data["sale_price"]
                    })
            else:
                flash("Error adding sale", "danger")

            return redirect(url_for("sales"))

        except Exception as e:
            logger.error(f"Error adding sale: {e}", exc_info=True)
            flash("Error adding sale", "danger")
            return redirect(url_for("sales"))

    return render_template("sales_form.html", sale=None, action="add")


# ============================
# SHIPPING
# ============================

@app.route("/shipping")
def shipping():
    """Shipping & dispatch page"""
    status_filter = request.args.get("status", "")

    shipments = db.get_shipments(status=status_filter if status_filter else None)

    return render_template(
        "shipping.html",
        shipments=shipments,
        status_filter=status_filter
    )


@app.route("/shipping/update/<shipment_id>", methods=["POST"])
def update_shipping(shipment_id):
    """Update shipment status"""
    try:
        shipment_data = {
            "status": request.form.get("status"),
            "tracking_number": request.form.get("tracking_number"),
            "carrier": request.form.get("carrier"),
            "notes": request.form.get("notes"),
        }

        if request.form.get("shipped_date"):
            shipment_data["shipped_date"] = request.form.get("shipped_date")
        if request.form.get("delivered_date"):
            shipment_data["delivered_date"] = request.form.get("delivered_date")

        success = db.update_shipment(shipment_id, shipment_data)
        if success:
            flash("Shipment updated", "success")
        else:
            flash("Error updating shipment", "danger")

    except Exception as e:
        logger.error(f"Error updating shipment: {e}", exc_info=True)
        flash("Error updating shipment", "danger")

    return redirect(url_for("shipping"))


# ============================
# RETURNS
# ============================

@app.route("/returns")
def returns():
    """Returns & disputes page"""
    status_filter = request.args.get("status", "")

    returns_data = db.get_returns(status=status_filter if status_filter else None)

    return render_template(
        "returns.html",
        returns=returns_data,
        status_filter=status_filter
    )


@app.route("/returns/add", methods=["GET", "POST"])
def add_return():
    """Add new return case"""
    if request.method == "POST":
        try:
            return_data = {
                "order_id": request.form.get("order_id"),
                "reason": request.form.get("reason"),
                "status": request.form.get("status", "Opened"),
                "date_opened": request.form.get("date_opened"),
                "expected_loss": float(request.form.get("expected_loss", 0)),
                "notes": request.form.get("notes"),
            }

            result = db.add_return(return_data)
            if result:
                flash("Return case added", "success")
            else:
                flash("Error adding return", "danger")

            return redirect(url_for("returns"))

        except Exception as e:
            logger.error(f"Error adding return: {e}", exc_info=True)
            flash("Error adding return", "danger")
            return redirect(url_for("returns"))

    return render_template("returns_form.html", return_case=None, action="add")


# ============================
# TASKS
# ============================

@app.route("/tasks")
def tasks():
    """Tasks & workflow page"""
    status_filter = request.args.get("status", "")

    tasks_data = db.get_tasks(status=status_filter if status_filter else None)

    return render_template(
        "tasks.html",
        tasks=tasks_data,
        status_filter=status_filter
    )


@app.route("/tasks/add", methods=["POST"])
def add_task():
    """Add new task"""
    try:
        task_data = {
            "title": request.form.get("title"),
            "description": request.form.get("description"),
            "category": request.form.get("category"),
            "priority": request.form.get("priority", "Medium"),
            "status": "Todo",
            "due_date": request.form.get("due_date") or None,
        }

        result = db.add_task(task_data)
        if result:
            flash("Task added", "success")
        else:
            flash("Error adding task", "danger")

    except Exception as e:
        logger.error(f"Error adding task: {e}", exc_info=True)
        flash("Error adding task", "danger")

    return redirect(url_for("tasks"))


@app.route("/tasks/update/<task_id>", methods=["POST"])
def update_task(task_id):
    """Update task status"""
    try:
        task_data = {
            "status": request.form.get("status"),
        }

        if task_data["status"] == "Done" and not request.form.get("completed_date"):
            task_data["completed_date"] = date.today().isoformat()

        success = db.update_task(task_id, task_data)
        if success:
            flash("Task updated", "success")
        else:
            flash("Error updating task", "danger")

    except Exception as e:
        logger.error(f"Error updating task: {e}", exc_info=True)
        flash("Error updating task", "danger")

    return redirect(url_for("tasks"))


@app.route("/tasks/delete/<task_id>", methods=["POST"])
def delete_task(task_id):
    """Delete task"""
    try:
        success = db.delete_task(task_id)
        if success:
            flash("Task deleted", "success")
        else:
            flash("Error deleting task", "danger")
    except Exception as e:
        logger.error(f"Error deleting task: {e}", exc_info=True)
        flash("Error deleting task", "danger")

    return redirect(url_for("tasks"))


# ============================
# SETTINGS
# ============================

@app.route("/settings")
def settings():
    """Settings page"""
    settings_data = db.get_all_settings()
    return render_template("settings.html", settings=settings_data)


@app.route("/settings/update", methods=["POST"])
def update_settings():
    """Update settings"""
    try:
        for key in ['currency', 'vinted_fee_percent', 'ebay_fee_percent', 'depop_fee_percent', 'paypal_fee_percent']:
            if request.form.get(key):
                db.set_setting(key, request.form.get(key))

        flash("Settings updated", "success")
    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        flash("Error updating settings", "danger")

    return redirect(url_for("settings"))


# ============================
# CSV IMPORT/EXPORT
# ============================

@app.route("/inventory/export")
def export_inventory():
    """Export inventory to CSV"""
    try:
        items = db.get_inventory(limit=10000)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'sku', 'item_name', 'category', 'size', 'condition', 'brand',
            'listing_status', 'purchase_price', 'sale_price', 'profit',
            'date_purchased', 'date_listed', 'date_sold', 'storage_location', 'notes'
        ])

        writer.writeheader()
        for item in items:
            row = {k: item.get(k, '') for k in writer.fieldnames}
            writer.writerow(row)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'inventory_export_{datetime.now().strftime("%Y%m%d")}.csv'
        )

    except Exception as e:
        logger.error(f"Error exporting inventory: {e}", exc_info=True)
        flash("Error exporting inventory", "danger")
        return redirect(url_for("inventory"))


@app.route("/sales/export")
def export_sales():
    """Export sales to CSV"""
    try:
        sales_data = db.get_sales(limit=10000)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            'order_id', 'platform', 'item_name', 'sale_price', 'platform_fees',
            'payment_processing_fees', 'shipping_cost', 'net_profit',
            'date_sold', 'payout_status', 'buyer_name'
        ])

        writer.writeheader()
        for sale in sales_data:
            row = {k: sale.get(k, '') for k in writer.fieldnames}
            writer.writerow(row)

        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode()),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sales_export_{datetime.now().strftime("%Y%m%d")}.csv'
        )

    except Exception as e:
        logger.error(f"Error exporting sales: {e}", exc_info=True)
        flash("Error exporting sales", "danger")
        return redirect(url_for("sales"))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting Awab Reselling Dashboard on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
