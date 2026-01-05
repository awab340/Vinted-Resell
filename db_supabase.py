"""
Database layer for Awab Reselling Dashboard using Supabase
Replaces the old SQLite-based db.py with Supabase PostgreSQL operations
"""

import os
from supabase import create_client, Client
from datetime import datetime, date
from typing import List, Dict, Optional, Any
from logger import get_logger

logger = get_logger(__name__)

# Initialize Supabase client
SUPABASE_URL = os.environ.get('SUPABASE_URL', '')
SUPABASE_KEY = os.environ.get('SUPABASE_ANON_KEY', '')

supabase: Client = None

def init_supabase():
    """Initialize Supabase client"""
    global supabase
    if not supabase:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.error("Supabase credentials not found in environment variables")
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized successfully")
    return supabase

# Initialize on import
init_supabase()


# ============================
# SETTINGS
# ============================

def get_setting(key: str) -> Optional[str]:
    """Get a setting value by key"""
    try:
        result = supabase.table('settings').select('value').eq('key', key).single().execute()
        return result.data['value'] if result.data else None
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return None

def set_setting(key: str, value: str):
    """Set or update a setting"""
    try:
        supabase.table('settings').upsert({
            'key': key,
            'value': value,
            'updated_at': datetime.now().isoformat()
        }).execute()
    except Exception as e:
        logger.error(f"Error setting {key}: {e}")

def get_all_settings() -> Dict[str, str]:
    """Get all settings as a dictionary"""
    try:
        result = supabase.table('settings').select('*').execute()
        return {row['key']: row['value'] for row in result.data}
    except Exception as e:
        logger.error(f"Error getting all settings: {e}")
        return {}


# ============================
# INVENTORY
# ============================

def get_inventory(limit: int = 50, status: Optional[str] = None, brand: Optional[str] = None) -> List[Dict]:
    """Get inventory items with optional filters"""
    try:
        query = supabase.table('inventory').select('*').order('created_at', desc=True)

        if status:
            query = query.eq('listing_status', status)
        if brand:
            query = query.eq('brand', brand)

        result = query.limit(limit).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting inventory: {e}")
        return []

def get_inventory_by_id(inventory_id: str) -> Optional[Dict]:
    """Get a single inventory item by ID"""
    try:
        result = supabase.table('inventory').select('*').eq('id', inventory_id).single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting inventory item {inventory_id}: {e}")
        return None

def get_inventory_by_sku(sku: str) -> Optional[Dict]:
    """Get a single inventory item by SKU"""
    try:
        result = supabase.table('inventory').select('*').eq('sku', sku).single().execute()
        return result.data
    except Exception as e:
        logger.debug(f"SKU {sku} not found: {e}")
        return None

def add_inventory_item(item_data: Dict) -> Optional[Dict]:
    """Add a new inventory item"""
    try:
        result = supabase.table('inventory').insert(item_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error adding inventory item: {e}")
        return None

def update_inventory_item(inventory_id: str, item_data: Dict) -> bool:
    """Update an inventory item"""
    try:
        item_data['updated_at'] = datetime.now().isoformat()
        supabase.table('inventory').update(item_data).eq('id', inventory_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating inventory item {inventory_id}: {e}")
        return False

def delete_inventory_item(inventory_id: str) -> bool:
    """Delete an inventory item"""
    try:
        supabase.table('inventory').delete().eq('id', inventory_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting inventory item {inventory_id}: {e}")
        return False

def get_inventory_stats() -> Dict:
    """Get inventory statistics"""
    try:
        all_items = supabase.table('inventory').select('listing_status, sale_price, purchase_price').execute()

        stats = {
            'total': len(all_items.data),
            'draft': sum(1 for item in all_items.data if item['listing_status'] == 'Draft'),
            'listed': sum(1 for item in all_items.data if item['listing_status'] == 'Listed'),
            'sold': sum(1 for item in all_items.data if item['listing_status'] == 'Sold'),
            'archived': sum(1 for item in all_items.data if item['listing_status'] == 'Archived'),
        }

        return stats
    except Exception as e:
        logger.error(f"Error getting inventory stats: {e}")
        return {'total': 0, 'draft': 0, 'listed': 0, 'sold': 0, 'archived': 0}


# ============================
# SALES
# ============================

def get_sales(limit: int = 50, platform: Optional[str] = None) -> List[Dict]:
    """Get sales with optional platform filter"""
    try:
        query = supabase.table('sales').select('*').order('date_sold', desc=True)

        if platform:
            query = query.eq('platform', platform)

        result = query.limit(limit).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting sales: {e}")
        return []

def get_sale_by_id(sale_id: str) -> Optional[Dict]:
    """Get a single sale by ID"""
    try:
        result = supabase.table('sales').select('*').eq('id', sale_id).single().execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting sale {sale_id}: {e}")
        return None

def add_sale(sale_data: Dict) -> Optional[Dict]:
    """Add a new sale"""
    try:
        result = supabase.table('sales').insert(sale_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error adding sale: {e}")
        return None

def update_sale(sale_id: str, sale_data: Dict) -> bool:
    """Update a sale"""
    try:
        sale_data['updated_at'] = datetime.now().isoformat()
        supabase.table('sales').update(sale_data).eq('id', sale_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating sale {sale_id}: {e}")
        return False

def delete_sale(sale_id: str) -> bool:
    """Delete a sale"""
    try:
        supabase.table('sales').delete().eq('id', sale_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting sale {sale_id}: {e}")
        return False

def get_sales_stats(days: int = 30) -> Dict:
    """Get sales statistics for the last N days"""
    try:
        # Get date N days ago
        from datetime import timedelta
        start_date = (datetime.now() - timedelta(days=days)).date().isoformat()

        result = supabase.table('sales').select('net_profit, platform').gte('date_sold', start_date).execute()

        total_profit = sum(float(sale['net_profit'] or 0) for sale in result.data)
        total_sales = len(result.data)

        # Sales by platform
        by_platform = {}
        for sale in result.data:
            platform = sale['platform']
            by_platform[platform] = by_platform.get(platform, 0) + 1

        return {
            'total_sales': total_sales,
            'total_profit': round(total_profit, 2),
            'by_platform': by_platform,
            'days': days
        }
    except Exception as e:
        logger.error(f"Error getting sales stats: {e}")
        return {'total_sales': 0, 'total_profit': 0, 'by_platform': {}, 'days': days}


# ============================
# SHIPMENTS
# ============================

def get_shipments(status: Optional[str] = None) -> List[Dict]:
    """Get shipments with optional status filter"""
    try:
        query = supabase.table('shipments').select('*, sales(order_id, item_name)').order('created_at', desc=True)

        if status:
            query = query.eq('status', status)

        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting shipments: {e}")
        return []

def get_pending_shipments() -> List[Dict]:
    """Get shipments that need action"""
    try:
        result = supabase.table('shipments').select('*, sales(order_id, item_name, buyer_name)').in_('status', ['Pending Label', 'Label Created']).order('dispatch_deadline', desc=False).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting pending shipments: {e}")
        return []

def add_shipment(shipment_data: Dict) -> Optional[Dict]:
    """Add a new shipment"""
    try:
        result = supabase.table('shipments').insert(shipment_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error adding shipment: {e}")
        return None

def update_shipment(shipment_id: str, shipment_data: Dict) -> bool:
    """Update a shipment"""
    try:
        shipment_data['updated_at'] = datetime.now().isoformat()
        supabase.table('shipments').update(shipment_data).eq('id', shipment_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating shipment {shipment_id}: {e}")
        return False


# ============================
# RETURNS
# ============================

def get_returns(status: Optional[str] = None) -> List[Dict]:
    """Get returns with optional status filter"""
    try:
        query = supabase.table('returns').select('*').order('date_opened', desc=True)

        if status:
            query = query.eq('status', status)

        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting returns: {e}")
        return []

def get_open_returns() -> List[Dict]:
    """Get open return cases"""
    try:
        result = supabase.table('returns').select('*').in_('status', ['Opened', 'In Progress']).order('date_opened', desc=True).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting open returns: {e}")
        return []

def add_return(return_data: Dict) -> Optional[Dict]:
    """Add a new return"""
    try:
        result = supabase.table('returns').insert(return_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error adding return: {e}")
        return None

def update_return(return_id: str, return_data: Dict) -> bool:
    """Update a return"""
    try:
        return_data['updated_at'] = datetime.now().isoformat()
        supabase.table('returns').update(return_data).eq('id', return_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating return {return_id}: {e}")
        return False


# ============================
# TASKS
# ============================

def get_tasks(status: Optional[str] = None) -> List[Dict]:
    """Get tasks with optional status filter"""
    try:
        query = supabase.table('tasks').select('*').order('due_date', desc=False, nullsfirst=False)

        if status:
            query = query.eq('status', status)

        result = query.execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting tasks: {e}")
        return []

def get_pending_tasks() -> List[Dict]:
    """Get pending and in-progress tasks"""
    try:
        result = supabase.table('tasks').select('*').in_('status', ['Todo', 'In Progress']).order('priority', desc=True).order('due_date', desc=False, nullsfirst=False).execute()
        return result.data
    except Exception as e:
        logger.error(f"Error getting pending tasks: {e}")
        return []

def add_task(task_data: Dict) -> Optional[Dict]:
    """Add a new task"""
    try:
        result = supabase.table('tasks').insert(task_data).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        return None

def update_task(task_id: str, task_data: Dict) -> bool:
    """Update a task"""
    try:
        task_data['updated_at'] = datetime.now().isoformat()
        supabase.table('tasks').update(task_data).eq('id', task_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error updating task {task_id}: {e}")
        return False

def delete_task(task_id: str) -> bool:
    """Delete a task"""
    try:
        supabase.table('tasks').delete().eq('id', task_id).execute()
        return True
    except Exception as e:
        logger.error(f"Error deleting task {task_id}: {e}")
        return False


# ============================
# DASHBOARD STATS
# ============================

def get_dashboard_stats() -> Dict:
    """Get comprehensive dashboard statistics"""
    try:
        inventory_stats = get_inventory_stats()
        sales_stats = get_sales_stats(30)
        pending_shipments = len(get_pending_shipments())
        open_returns_count = len(get_open_returns())
        pending_tasks = len(get_pending_tasks())

        return {
            'inventory': inventory_stats,
            'sales_30d': sales_stats,
            'pending_shipments': pending_shipments,
            'open_returns': open_returns_count,
            'pending_tasks': pending_tasks
        }
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        return {}
