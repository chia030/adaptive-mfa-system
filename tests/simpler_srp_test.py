# testing the flow of SRP (both for client and server sides)

import srp

salt, vkey = srp.create_salted_verification_key('test', 'test')

class AuthenticationFailed (Exception):
    pass

usr = srp.User('test', 'test')
uname, A = usr.start_authentication()

print(f"Authentication Started, uname = {uname} | A = {A.hex()}")

# client => server: username, A
svr = srp.Verifier(uname, salt, vkey, A)
s, B = svr.get_challenge()

print(f"Server get challenge, s = {s.hex()} | B = {B.hex()}")

if s is None or B is None:
    raise AuthenticationFailed()

# server => client: s, B
M = usr.process_challenge(s, B)

print(f"Client process challenge, M = {M.hex()}")

if M is None:
    raise AuthenticationFailed()

# client => server: M
HAMK = svr.verify_session(M)

print(f"Server verify session, HAMK = {HAMK.hex()}")
print(f"Server Session Key, K = {svr.get_session_key().hex()}")

if HAMK is None:
    raise AuthenticationFailed()

# server => client: HAMK
output = usr.verify_session(HAMK)

print(f"Client verify session output {output}")
print(f"Client Session Key, K = {usr.get_session_key().hex()}")

# authentication complete
assert usr.authenticated()
assert svr.authenticated()