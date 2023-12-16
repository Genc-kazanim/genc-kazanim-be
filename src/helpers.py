import os
import json
import qrcode
import requests
from web3 import Web3
from uuid import uuid4
from loguru import logger
from pinatapy import PinataPy
from eth_account.messages import encode_defunct
from dotenv import load_dotenv
load_dotenv()
import os



def verify_signature(event_name, event_id, timestamp, signature, signer_address):
    w3 = Web3(Web3.HTTPProvider(f'https://mainnet.infura.io/v3/{os.getenv("INFURA_PROJECT_ID")}'))

    message = json.dumps({"event_name": event_name, "event_id": event_id, "timestamp": timestamp})
    encoded_message = encode_defunct(text=message)

    recovered_address = w3.eth.account.recover_message(encoded_message, signature=signature)

    return recovered_address.lower() == signer_address.lower()

def verify_organizer_signature(event_id, signature, signer_address):
    w3 = Web3(Web3.HTTPProvider('https://mainnet.infura.io/v3/ee4bc82de5f942b5b9270c7dce828537'))

    message = json.dumps({"event_id": event_id})
    encoded_message = encode_defunct(text=message)

    recovered_address = w3.eth.account.recover_message(encoded_message, signature=signature)

    return recovered_address.lower() == signer_address.lower()
def create_json_and_qr_code(event_name, event_id, timestamp):
    data = {
        "event_name": event_name,
        "event_id": event_id,
        "timestamp": timestamp
    }

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )

    qr.add_data(json.dumps(data))
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    qr_image_filename = f'{uuid4()}.png'
    img.save(qr_image_filename)

    qr_ipfs_hash = upload_pinata(qr_image_filename)
    os.remove(qr_image_filename)

    return qr_ipfs_hash


def upload_pinata(filename):
    pinata = PinataPy(f'{os.getenv("PINATA_API_KEY")}', f'{os.getenv("PINATA_SECRET_KEY")}')
    response = pinata.pin_file_to_ipfs(filename)

    logger.info(response)
    return response['IpfsHash']


# if __name__ == "__main__":
#     print(verify_organizer_signature("bfe7f7a6-9e7e-4135-afdf-0b038050dc9c",
#                                      "0x86935a9fbcab7563585292bf8d96fb243dc48c411a3b0d5858bcc07c7d2807b40bf7d0c4605d6a6cc83f1be812a96124040bdad9923eb49c5c05efc0eb0a886a1b",
#                                      "0x91bd6e4353c93a2faaa683614a283efcd85d18e1"))
