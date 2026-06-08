"""
order_processor.py
------------------
Bug-ridden order processing module.
There are THREE intentional bugs. Find them all.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json


class OrderProcessor:
    TAX_RATE = 0.08  # 8% tax
    SHIPPING_THRESHOLD = 50.0  # free shipping above this amount
    EXPRESS_SURCHARGE = 12.99

    def __init__(self):
        self.orders: List[Dict] = []
        self._processed_count = 0

    def add_order(self, order_id: str, items: List[Dict], customer_tier: str = "standard") -> Dict:
        """Add a new order. Items format: [{'name': str, 'price': float, 'qty': int}, ...]"""
        subtotal = sum(item['price'] * item['qty'] for item in items)

        order = {
            'order_id': order_id,
            'items': items,
            'subtotal': subtotal,
            'tax': subtotal * self.TAX_RATE,
            'shipping': 0.0 if subtotal >= self.SHIPPING_THRESHOLD else 5.99,
            'total': 0.0,
            'customer_tier': customer_tier,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        # BUG 1: total is calculated BEFORE tax is added to subtotal+shipping
        order['total'] = order['subtotal'] + order['shipping']

        # Apply customer tier discounts
        if customer_tier == "premium":
            order['total'] *= 0.9  # 10% off
        elif customer_tier == "vip":
            order['total'] *= 0.8  # 20% off

        self.orders.append(order)
        return order

    def process_batch(self, order_ids: List[str]) -> Dict:
        """Process multiple orders. Returns summary."""
        results = {'processed': [], 'failed': [], 'total_revenue': 0.0}

        for oid in order_ids:
            order = self.find_order(oid)
            if not order:
                results['failed'].append({'order_id': oid, 'reason': 'not found'})
                continue

            # BUG 2: status check is wrong — checks 'processing' instead of 'pending'
            if order['status'] == 'processing':
                order['status'] = 'processed'
                order['processed_at'] = datetime.now().isoformat()
                self._processed_count += 1
                results['processed'].append(oid)
                results['total_revenue'] += order['total']
            else:
                results['failed'].append({'order_id': oid, 'reason': f"wrong status: {order['status']}"})

        # BUG 3: rounding error — revenue should be rounded to 2 decimals
        return results

    def find_order(self, order_id: str) -> Optional[Dict]:
        for order in self.orders:
            if order['order_id'] == order_id:
                return order
        return None

    def apply_express_shipping(self, order_id: str) -> bool:
        order = self.find_order(order_id)
        if order and order['status'] == 'pending':
            order['shipping'] += self.EXPRESS_SURCHARGE
            order['total'] += self.EXPRESS_SURCHARGE
            return True
        return False

    def get_daily_summary(self) -> Dict:
        today = datetime.now().date()
        today_orders = [
            o for o in self.orders
            if datetime.fromisoformat(o['created_at']).date() == today
        ]
        return {
            'count': len(today_orders),
            'revenue': sum(o['total'] for o in today_orders),
            'tiers': {tier: len([o for o in today_orders if o['customer_tier'] == tier]) for tier in ['standard', 'premium', 'vip']}
        }
