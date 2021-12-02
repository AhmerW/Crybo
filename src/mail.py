from typing import List
from datetime import date, datetime
import os

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


from dotenv import load_dotenv

from mathfuncs import calculate_increase


load_dotenv(".env")

MAIL_RECIPIENTS = [
    os.getenv("recipient1"),
    os.getenv("recipient2"),
]


MAIL_USERNAME = os.getenv("MAIL-USERNAME")
MAIL_PWD = os.getenv("MAIL-PWD")


def send_email(message, recipients):

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.ehlo()
        server.starttls()
        server.login(
            MAIL_USERNAME,
            MAIL_PWD,
        )
        server.sendmail(
            MAIL_USERNAME,
            recipients,
            message,
        )
        server.close()
    except Exception as e:
        print(f"exception: {e}")
        raise e


def send_crypto_mail(cryptos: List[dict]):
    msg = MIMEMultipart("alternative")

    mail_data = {
        "from": MAIL_USERNAME,
        "to": ", ".join(MAIL_RECIPIENTS),
        "subject": f"Crybo | {len(cryptos)} coin{'s' if len(cryptos) > 1 else ''}",
    }
    for k, v in mail_data.items():
        msg[k] = v

    text = f"{len(cryptos)} coin{'s' if len(cryptos) > 1 else ''}"
    html = generate_html(cryptos)
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    send_email(
        msg.as_string(),
        MAIL_RECIPIENTS,
    )


def generate_html(cryptos: List[dict]):
    html = """\
<!DOCTYPE html>
<html>
<head>
<style>
table {
  font-family: arial, sans-serif;
  border-collapse: collapse;
  width: 100%;
}

td, th {
  border: 1px solid #dddddd;
  text-align: left;
  padding: 8px;
}

tr:nth-child(even) {
  background-color: #dddddd;
}
</style>
</head>
<body>

<h2>Crypto data</h2>

<table>
  <tr>
    <th>Ticker</th>
    <th>Name</th>
    <th>initial price</th>
    <th>Increase</th>
    <th>Last scan price</th>
    <th>Last scan time</th>
  </tr>



    """

    for crypto in cryptos:
        try:
            increase = calculate_increase(
                crypto["inital-price"], crypto["initial_price"]
            )

        except Exception as e:

            increase = 100
        html += f"""
        <tr>
            <td>{crypto.get('id')}</td>
            <td>{crypto.get('name')}</td>
            <td>{crypto.get('initial-price')}</td>
            <td>{increase}% ({increase / 100}x)</td>
            <td>{crypto.get('last-checked-price')}</td>
            <td>{str(datetime.fromtimestamp(crypto.get('last-checked-ts', 0)))}</td>
        </tr>
        """

    html += """
</table>

</body>
</html>
        """
    return html
