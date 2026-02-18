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
            first_parts = parts[1].strip().split()
            # Skip leading initials (single letter or letter+period) to find
            # the actual first name.
            # e.g., "REDISH, A DAVID" → "David"
            #       "DUDLEY, R. ADAMS" → "Adams"
            #       "ROSSER, B R SIMON" → "Simon"
            first_name = first_parts[0]
            for part in first_parts:
                stripped = part.rstrip(".")
                if len(stripped) == 1 and len(first_parts) > first_parts.index(part) + 1:
                    continue  # skip initial
                first_name = part
                break
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
        # Try progressively looser filters; exact givenName first to avoid
        # prefix collisions (e.g., "Carol" vs "Carolyn")
        filters = [
            f"(&(sn={last_name})(givenName={first_name}))",
            f"(&(sn={last_name})(givenName={first_name}*))",
            f"(&(sn={last_name}*)(givenName={first_name}*))",
            f"(&(sn={last_name}*)(givenName={first_name[0]}*))",
        ]
        
        attributes = ["cn", "sn", "givenName", "mail", "title", "ou", "o", "displayName"]
        
        # Track best candidate across ALL filters.
        # Only return early on an exact first-name match (score 2).
        # This prevents e.g., "Carolyn" (prefix match via sn=Peterson)
        # from beating "Carol" (exact match, but only found via sn=Peterson*
        # because her sn is "Peterson PhD").
        overall_best = None
        overall_best_score = -1

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

                    # Verify this is a reasonable match - check both first AND last name
                    if not (last_name.lower() in (surname or "").lower() and
                            given and first_name and
                            first_name[0].lower() == given[0].lower()):
                        continue

                    # Score: exact first name > prefix > initial-only
                    if given.lower() == first_name.lower():
                        score = 2  # exact match
                    elif given.lower().startswith(first_name.lower()):
                        score = 1  # prefix match (e.g., "Carol" in "Carolina")
                    else:
                        score = 0  # initial-only match

                    if score > overall_best_score:
                        overall_best_score = score
                        overall_best = {
                            "dn": entry.entry_dn,
                            "rank": title,
                            "department": ou,
                            "organization": organization or "University of Minnesota",
                            "source": "LDAP (UMN)"
                        }

                    if overall_best_score == 2:
                        return overall_best  # exact match, done

            except Exception as e:
                continue

        return overall_best
        
    except Exception as e:
        print(f"    Error during LDAP lookup: {e}")
        return None
if __name__ == "__main__":
    # Test with known PI
    details = get_pi_details("LIM, KELVIN", "University of Minnesota")
    print(f"Result: {details}")