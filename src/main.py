import os
import sys
import json
import atexit
from time import sleep, time
from datetime import datetime
from typing import Final, List

import dotenv
import requests

from mathfuncs import calculate_increase, increase_x
from mail import send_crypto_mail


dotenv.load_dotenv(".env")


BLACKLISTS = ["realt"]
BASE_URL = "https://api.coingecko.com/api/v3/"  # api url
INTERVAL = 500  # market check interval (INTERVAL seconds)

MAIL_CHUNK = 20  # not implemented, but max MAIL_CHUNK coins per mail
MAIL_CHUNK_DELAY = 1000  # wait MAIL_CHUNK_DELAY coins before sending mail

CHUNKS = 45  # Fetch in chunks of CHUCNKS coins
CHUNK_BREAKS = [
    22
]  # Break at CHUNCK_BREAKS during the chuck and wait for CHUNK_BREAK_DELAY Secoonds
CHUNK_BREAK_DELAY = 5  # Duration of the chunk break in seconds
CHUNK_DELAY = 60  # Wait CHUNCK_DELAY seconds between chunks

INCR_ALERT = 2  # will allert on (INCR_ALERT)x increase
CURRENCY = "usd"


def make_url(url) -> str:
    return f"{BASE_URL}{url}"


def make_request(url) -> dict:
    response = requests.get(make_url(url))

    if response.status_code != 404 and response.status_code != 200:
        is_error = True

        cprint(Colors.RED, f"Error Code: {response.status_code}")
        try:
            response.json()
            if response.get("error"):
                cprint(Colors.RED, f"Error: {response.json()['error']}")

            is_error = False
        except:
            pass

        if is_error:
            cprint(Colors.RED, f"! RATELIMIT ! {response.text}")
            cprint(Colors.YELLOW, f"\n\n[Saving state]")
            stateContainer.save_state_file()
            sys.exit()

    return response.json()


class Colors:
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    END = "\033[0m"


def cprint(color: Colors, text: str) -> None:
    print(Colors.END, f"{color}{text}{Colors.END}")


# Coin template
"""
{
    "name": "name",
    "id": "id",
    "initial-price": "",
    "last-checked-price": "",
    "last-checked-ts": null,
    "mail-sent": false,
    "mail-sent-ts": null,
    "currency": "usd",
}
"""


class StateContainer:
    def __init__(self) -> None:
        self.preload()
        self._state: List[dict] = self.get_state_file().get(
            "coins", []
        )  # type: List[dict]

    @property
    def state(self) -> dict:
        return self._state

    def set_state(self, new_state: dict) -> None:
        self._state = new_state

    def state_is_empty(self) -> bool:
        return not self.state

    def preload(self):
        if not "logs" in os.listdir():
            os.mkdir("logs")

        if not os.path.exists("state.json"):
            with open("state.json", "w+") as f:
                f.write('{"coins": []}')

    def get_state_file(self) -> dict:
        with open("state.json", "r") as f:
            return json.load(f)

    def save_state_file(self) -> None:
        with open("state.json", "w") as f:
            json.dump({"coins": self.state}, f)


stateContainer: Final[StateContainer] = StateContainer()


def price_is_match(initial_price: int, current_price: int, incr: int) -> bool:
    return (initial_price * (incr)) <= current_price


def write_to_log_date_file(title: str, content: str):
    with open(
        os.path.join(
            "logs",
            f"{title}-{datetime.now().strftime('%Y-%m-%d-%H-%M-%S')}.log",
        ),
        "w+",
    ) as f:
        f.write(content)


def check_market() -> None:
    if stateContainer.state_is_empty():
        coins = make_request("coins/list")

        stateContainer.set_state(coins)
        stateContainer.save_state_file()
        del coins

    state = stateContainer.state
    INCR = INCR_ALERT - 0.3
    chunk = 0
    checked_coins = 0

    for_mail = []

    for i, coin in enumerate(state):
        blacklisted = False
        name = coin.get("name")
        for blacklist in BLACKLISTS:
            if blacklist in name.lower():
                cprint(
                    Colors.RED,
                    f"{Colors.MAGENTA} {name} {Colors.RED} is blacklisted {Colors.END}",
                )
                blacklisted = True

        if blacklisted:
            continue

        if checked_coins % MAIL_CHUNK_DELAY == 0:

            if checked_coins > 0:
                stateContainer.save_state_file()

            if for_mail:

                send_crypto_mail([d[1] for d in for_mail])
                for data in for_mail:
                    index, coin = data
                    cprint(
                        Colors.GREEN,
                        f"{coin['name']} is {coin['last-checked-price']}. {Colors.BLUE} Mail sent {Colors.END}",
                    )

                    state[index]["mail-sent"] = True
                    state[index]["mail-sent-ts"] = time()

                for_mail.clear()

        if chunk >= CHUNKS:
            cprint(
                Colors.YELLOW,
                f"{chunk}/{CHUNKS} chunks. Waiting {CHUNK_DELAY} seconds.",
            )
            chunk = 0
            sleep(CHUNK_DELAY)
            cprint(Colors.YELLOW, "Continuing")
        elif chunk in CHUNK_BREAKS:
            cprint(
                Colors.YELLOW,
                f"{chunk}/{CHUNKS} chunks. Break for {CHUNK_BREAK_DELAY} seconds.",
            )
            sleep(CHUNK_BREAK_DELAY)
            cprint(Colors.YELLOW, "Continuing")

        chunk += 1
        coin_data = make_request(f"coins/{coin['id']}/")
        coin_currency = coin.get("currency", CURRENCY)
        try:
            checked_coins += 1

            if not coin.get("initial-price"):
                cprint(
                    Colors.RED,
                    f"{Colors.MAGENTA} {coin.get('name')} {Colors.RED} not found in records {Colors.END}",
                )
                state[i] = {
                    "name": coin_data["name"],
                    "id": coin_data["id"],
                    "initial-price": coin_data["market_data"]["current_price"][
                        coin_currency
                    ],
                    "last-checked-price": coin_data["market_data"]["current_price"][
                        coin_currency
                    ],
                    "last-checked-ts": time(),
                    "mail-sent": False,
                    "mail-sent-ts": None,
                    "currency": coin_currency,
                }
                continue

            current_price = coin_data["market_data"]["current_price"][coin_currency]
            initial_price = coin["initial-price"]
            last_checked_price = coin["last-checked-price"]

            if current_price - last_checked_price < 0:
                try:
                    decrease = round(
                        (last_checked_price - current_price) / last_checked_price * 100,
                        2,
                    )

                except:
                    decrease = 0
                cprint(
                    Colors.WHITE,
                    f"\033[35m {coin.get('name')} \033[0m current price: {current_price} {coin_currency}. [Down '-{decrease}%' (-{round(decrease/100, 2)}x)]",
                )
                continue

            cprint(
                Colors.WHITE,
                f"\033[35m {coin.get('name')} \033[0m current price: {current_price} {coin_currency}",
            )

            grtr_than_initial = price_is_match(
                initial_price,
                current_price,
                INCR,
            )
            grtr_than_last_checked = price_is_match(
                last_checked_price, current_price, INCR
            )

            if grtr_than_initial or grtr_than_last_checked:
                try:

                    increase = int(
                        calculate_increase(last_checked_price, initial_price)
                    )
                except Exception as e:
                    increase = 100

                cprint(
                    Colors.GREEN,
                    f"{increase}% ({increase_x(increase)}x) since last checked",
                )
                if grtr_than_last_checked:
                    state[i]["mail-sent"] = False

                state[i]["last-checked-price"] = current_price
                state[i]["last-checked-ts"] = time()

                if state[i]["mail-sent"]:
                    cprint(Colors.RED, f"{name} - Mail already sent")
                    continue

                for_mail.append((i, coin))

            else:
                # cprint(Colors.RED, f"Price not {INCR_ALERT}x since last checked")
                pass

        except (KeyError, ValueError):
            continue

    stateContainer.save_state_file()


@atexit.register
def onexit():
    cprint(Colors.RED, "Exiting")
    cprint(Colors.YELLOW, "Saving state")
    stateContainer.save_state_file()


def start() -> None:
    market_checks = 1
    while True:
        check_market()
        write_to_log_date_file(
            f"market-check-{market_checks}-done",
            "",
        )

        market_checks += 1
        cprint(Colors.END, f"Done checking market. Sleeping {INTERVAL}")
        sleep(INTERVAL)


if __name__ == "__main__":
    start()
