from server.ldap import ldap_login

# additional Dummy / Test users
# (-> remove these users for production)
additional_users = {
	"tutor_username":{"pw":"123","fullname":"Tutor"},
	"admin_username":{"pw":"123","fullname":"Admin"},
	"test1":{"pw":"123","fullname":"Test User1"},
	"test2":{"pw":"123","fullname":"Test User2"},
	"test3":{"pw":"123","fullname":"Test User3"}
}


def login(username,password):
	"""
	check if (username,password) are valid login credentials. If true: return fullname. Else: return None
	:username: username (string)
	:password: password (string)
	:return: fullname or None
	"""
	
	# check additional users
	if username in additional_users.keys():
		if password!=additional_users[username]["pw"]:
			return None
		
		return additional_users[username]["fullname"]
	
	user = ldap_login(username, password)
	return None if user is None else user["fullname"]
