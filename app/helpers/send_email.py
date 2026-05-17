# All comments are made by a human. Not AI.

"""
Email Handler

Because this is just a school project, Gmail will be the primary email handler.
Move onto professional transactional email providers like Plunk on prod.
"""

import smtplib
import os

def send_verification_email(to_email, fullname, verification_link):
    # Draft the email
    subject = "Verify your email for VinafcoConnect"
    html_body = f"""
    <html>
        <body>
            <h3>Thank you, {fullname}, for signing up to VinafcoConnect</h3>
            <p>Please click the link below to verify your email:</p>
            <a href="{os.getenv('BACKEND_URL')}/auth/verify-email?token={verification_link}">Click here</a>
        </body>
    </html>
    """
    
    # Send the email using Gmail SMTP
    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), os.getenv("EMAIL_PORT")) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            message = f"Subject: {subject}\nContent-Type: text/html\n\n{html_body}"
            server.sendmail(os.getenv("EMAIL_ADDRESS"), to_email, message)
            return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False
    
def send_sso_email(to_email, sso_link):
    # Draft the email
    subject = "Your VinafcoConnect SSO Link"
    html_body = f"""
    <html>
        <body>
            <h3>Your Single Sign-On Link for VinafcoConnect</h3>
            <p>Please click the link below to access your account:</p>
            <a href="{sso_link}">{sso_link}</a>
        </body>
    </html>
    """
    
    # Send the email using Gmail SMTP
    try:
        with smtplib.SMTP(os.getenv("EMAIL_HOST"), os.getenv("EMAIL_PORT")) as server:
            server.starttls()
            server.login(os.getenv("EMAIL_ADDRESS"), os.getenv("EMAIL_PASSWORD"))
            message = f"Subject: {subject}\nContent-Type: text/html\n\n{html_body}"
            server.sendmail(os.getenv("EMAIL_ADDRESS"), to_email, message)
            return True
    except Exception as e:
        print(f"Error sending email: {e}")
        return False