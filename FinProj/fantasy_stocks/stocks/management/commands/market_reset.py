from typing import List
from models.inventory import Inventory
from models.marketplace import Marketplace
from models.user_listing import UserListing

def reset_all_inventories() -> None:
    # Reset all inventories
    Inventory.objects.all().delete()
    print("All inventories have been reset.")

def reset_all_marketplace_listings() -> None:
    # Reset all marketplace listings
    Marketplace.objects.all().delete()
    print("All marketplace listings have been reset.")

def reset_all_user_listings() -> None:
    # Reset all user listings
    UserListing.objects.all().delete()
    print("All user listings have been reset.")

def reset_all() -> List[str]:
    reset_functions = [
        reset_all_inventories,
        reset_all_marketplace_listings,
        reset_all_user_listings
    ]
    
    results = []
    for func in reset_functions:
        try:
            func()
            results.append(f"{func.__name__} completed successfully.")
        except Exception as e:
            results.append(f"{func.__name__} failed: {str(e)}")
    
    return results

# Command execution
if __name__ == "__main__":
    print("Initiating reset sequence...")
    results = reset_all()
    for result in results:
        print(result)
    print("Reset sequence complete. 'Welcome to the desert of the real.'")