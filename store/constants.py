from enum import StrEnum

class ProductCategory(StrEnum):
    ELECTRONICS = "Electronics"
    CLOTHING = "Clothing"
    FOOTWEAR = "Footwear"
    HOME_KITCHEN = "Home & Kitchen"
    BOOKS = "Books"
    TOYS_GAMES = "Toys & Games"

    @classmethod
    def choices(cls):
        return [(category.value, category.name.replace("_", " ").title()) for category in cls]


class OrderStatus(StrEnum):
    PENDING = "Pending"
    PAID = "Paid"
    PROCESSING = "Processing"
    SHIPPED = "Shipped"
    OUT_FOR_DELIVERY = "Out for delivery"
    DELIVERED = "Delivered"
    CANCELLED = "Cancelled"
    REFUNDED = "Refunded"

    @classmethod
    def choices(cls):
        return [(status.value, status.name.replace("_", " ").title()) for status in cls]


