from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPException

# LDAP server configuration (Attention: to connect to the LDAP server, you might need VPN)
LDAP_ENDPOINT = "ldap://apoll.informatik.uni-bonn.de"
BIND_DN = "cn=ldapbrowse,cn=Users,dc=informatik,dc=uni-bonn,dc=de"
BIND_PW = "browse.me"
USER_BASE = "dc=informatik,dc=uni-bonn,dc=de"

def ldap_login(username, password):
	"""
	Authenticates a user using LDAP.
	:param username: The username of the user.
	:param password: The password of the user.
	:return: User information if authentication is successful, None otherwise.
	"""
	
	# check ldap
	try:
		# Connect and bind as a service account
		server = Server(LDAP_ENDPOINT, get_info=ALL)
		with Connection(server, user=BIND_DN, password=BIND_PW, auto_bind=True) as conn:
			# Search for the user
			search_filter = f"(&(objectClass=user)(!(objectClass=computer))(uidNumber=*)(unixHomeDirectory=*)(sAMAccountName={username}))"
			conn.search(
				search_base=USER_BASE,
				search_filter=search_filter,
				search_scope=SUBTREE,
				attributes=["sAMAccountName", "givenName", "sn"],  # Explicit attributes
			)

			if not conn.entries:
				return None  # User not found

			# Attempt to bind with the user's credentials to verify them
			user_dn = conn.entries[0].entry_dn  # Correct way to access DN
			with Connection(server, user=user_dn, password=password, auto_bind=True):
				# Authentication successful
				return {
					"username": conn.entries[0].sAMAccountName.value,
					"fullname": conn.entries[0].givenName.value+" "+conn.entries[0].sn.value
				}
	except LDAPException as e:
		print(f"LDAP authentication failed: {e}")
		return None

def ldap_users():
	"""
	Lists all users in the LDAP directory.
	:return: A list of user dictionaries containing relevant attributes.
	"""
	users = []
	try:
		# Connect and bind as a service account
		server = Server(LDAP_ENDPOINT, get_info=ALL)
		with Connection(server, user=BIND_DN, password=BIND_PW, auto_bind=True) as conn:
			# Search for users
			search_filter = "(&(objectClass=user)(!(objectClass=computer))(uidNumber=*)(unixHomeDirectory=*)(sAMAccountName=*))"
			conn.search(
				search_base=USER_BASE,
				search_filter=search_filter,
				search_scope=SUBTREE,
				attributes=["sAMAccountName", "givenName", "sn"],  # Explicit attributes
			)

			# Process and format user entries
			for entry in conn.entries:
				dn_tokens = entry.entry_dn.split(",")  # Correctly accessing DN
				users.append({
					"username": entry.sAMAccountName.value,
					"fullname": conn.entries[0].givenName.value+" "+conn.entries[0].sn.value,
					"is_staff": any("OU=Mitarbeiter" in token for token in dn_tokens),
					"is_group": any("OU=2RK" in token for token in dn_tokens),
				})
	except LDAPException as e:
		print(f"LDAP user listing failed: {e}")
	return users

