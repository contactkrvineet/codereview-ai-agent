"""
Intentionally bad code — used to verify the code review agent catches violations.
DO NOT merge this file.
"""

import time
import requests


# Violation: hardcoded secret (security - high)
API_KEY = "AIzaSyB_hardcoded_secret_key_do_not_commit"
DB_PASSWORD = "SuperSecret123!"


def d(x, y):
    # Violation: single-letter function name and parameters (naming - medium)
    # Violation: magic number (magic-number - medium)
    return x * y + 42


def fetch_user_data(id):
    # Violation: bare except swallowing the exception silently (error-handling - high)
    try:
        response = requests.get(f"http://api.example.com/users/{id}?key={API_KEY}")
        return response.json()
    except:
        pass


def process_orders(orders):
    results = []
    for o in orders:
        # Violation: magic number (magic-number - medium)
        if o["amount"] > 9999:
            # Violation: Thread.sleep / time.sleep in processing logic (magic-number - medium)
            time.sleep(5)
            results.append(o)
    # Violation: function returns without handling empty case
    return results


class userAccount:
    # Violation: class name not PascalCase (naming - medium)

    def __init__(self):
        # Violation: hardcoded URL in business logic (magic-number - medium)
        self.base_url = "http://internal-api.corp.example.com:8080"
        self.timeout = 30

    def checkUser(self, u, p):
        # Violation: boolean parameter controlling behaviour (naming - low)
        # Violation: hardcoded credentials (security - high)
        if u == "admin" and p == "admin123":
            return True
        return False


def testLogin():
    # Violation: test has no assertion (test-quality - high)
    # Violation: test name doesn't describe behaviour (test-quality - medium)
    acc = userAccount()
    acc.checkUser("admin", "admin123")


def testit():
    # Violation: test name is meaningless (test-quality - medium)
    # Violation: test has no assertion (test-quality - high)
    fetch_user_data(1)
