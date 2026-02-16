from ldap3 import Server, Connection, ALL
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Strip quotes from environment variables if present
LDAP_SERVER = os.getenv("LDAP_SERVER", "ldap://ldap.umn.edu:389").strip("'\"")
LDAP_BASE_DN = os.getenv("BASE_DN", "o=University of Minnesota,c=US").strip("'\"")
LDAP_BIND_DN = os.getenv("BIND_DN", "").strip("'\"")
LDAP_LOGIN = os.getenv("LDAP_LOGIN", "").strip("'\"")
LDAP_PASSWORD = os.getenv("LDAP_PASSWORD", "").strip("'\"")

def create_ldap_connection():
    """
    Creates and returns an LDAP connection.
    Tries authenticated bind first, falls back to anonymous.
    """
    try:
        server = Server(LDAP_SERVER, get_info=ALL, connect_timeout=10)
        
        # Try with credentials first
        if LDAP_BIND_DN and LDAP_PASSWORD:
            try:
                conn = Connection(server, user=LDAP_BIND_DN, password=LDAP_PASSWORD, auto_bind=True)
                print(f"✓ Connected to LDAP as {LDAP_LOGIN}")
                return conn
            except Exception as auth_error:
                print(f"✗ Authenticated bind failed ({auth_error}), trying anonymous...")
        
        # Fall back to anonymous
        conn = Connection(server, auto_bind=True)
        print(f"✓ Connected to LDAP anonymously")
        return conn
        
    except Exception as e:
        print(f"✗ Error creating LDAP connection: {e}")
        return None


def get_pi_details(contact_pi_name, conn, org_name="University of Minnesota"):
    """
    Retrieves PI details (Rank, Department, School) from UMN LDAP server.
    Uses an existing ldap3 connection (reused across multiple lookups).
    """
    # Parse name (Assuming "Last, First" or "Last, First M")
    try:
        if "," in contact_pi_name:
            parts = contact_pi_name.split(",")
            last_name = parts[0].strip()
            first_name = parts[1].strip().split(" ")[0]  # Take first part of first name
        else:
            # Fallback for "First Last"
            parts = contact_pi_name.split(" ")
            last_name = parts[-1]
            first_name = parts[0]
    except Exception as e:
        print(f"    Error parsing name {contact_pi_name}: {e}")
        return None

    try:
        # Search using sn (surname) and givenName
        # Try multiple search attempts with different filter combinations
        filters = [
            f"(&(sn={last_name})(givenName={first_name}))",
            f"(&(sn={last_name})(givenName={first_name[0]}*))",
            f"(sn={last_name})",
        ]
        
        attributes = ["cn", "sn", "givenName", "mail", "title", "ou", "o", "displayName"]
        
        for search_filter in filters:
            try:
                conn.search(LDAP_BASE_DN, search_filter, attributes=attributes)
                
                if not conn.entries:
                    continue
                
                for entry in conn.entries:
                    # Extract attributes
                    cn = entry.cn[0] if entry.cn else None
                    given = entry.givenName[0] if entry.givenName else None
                    surname = entry.sn[0] if entry.sn else None
                    title = entry.title[0] if entry.title else None
                    ou = entry.ou[0] if entry.ou else None
                    organization = entry.o[0] if entry.o else None
                    
                    # Verify this is a reasonable match
                    if last_name.lower() in (surname or "").lower():
                        return {
                            "dn": entry.entry_dn,
                            "rank": title,
                            "department": ou,
                            "organization": organization or "University of Minnesota",
                            "source": "LDAP (UMN)"
                        }
                
                # If we got results but no good match, try next filter
                
            except Exception as e:
                continue
        
        return None
        
    except Exception as e:
        print(f"    Error during LDAP lookup: {e}")
        return None
if __name__ == "__main__":
    # Test with known PI
    details = get_pi_details("LIM, KELVIN", "University of Minnesota")
    print(f"Result: {details}")