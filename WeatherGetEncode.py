import sys
import time
import jwt
import os
from dotenv import load_dotenv
# Open PEM
ALGORITHM = "EdDSA"

class encoder:
    def __init__(self, privateKey:str=None,projectId:str=None,credentialId:str=None):
        load_dotenv()
        self.privateKey  =privateKey or os.getenv("WEATHER_KEY")
        self.projectId  =projectId or os.getenv("PROJECT_ID")
        self.credentialId  =credentialId or os.getenv("CREDENTIAL_ID")
    def encodeJWT(self)->str:
        payload = {
            'iat':int(time.time()) -30,
            'exp':int(time.time()) +900,
            'sub':self.projectId
        }
        headers = {
            'kid': self.credentialId
        }
        # Generate JWT
        encoded_jwt = jwt.encode(
            payload, self.privateKey, ALGORITHM, headers = headers
            )

        return encoded_jwt
if __name__ == "__main__":
    endcoder = encoder()
    print(endcoder.encodeJWT())