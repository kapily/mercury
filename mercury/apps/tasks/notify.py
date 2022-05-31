import os
from django.conf import settings
from django.core.mail import (send_mail, EmailMessage)
from django.contrib.auth.models import User
from apps.tasks.tasks_export import export_to_pdf


def valid_notify(config):
    return True


def username_to_email(username):
    users = User.objects.filter(username=username)
    if not users:
        return ""
    # not worry about duplicates in username
    return users[0].email


def list_to_emails(contacts):
    emails = []
    for contact in contacts:
        contact = contact.strip()
        if "@" in contact:
            emails += [contact]
        else:
            email_address = username_to_email(contact)
            if email_address:
                emails += [email_address]
    return list(set(emails))


def parse_config(config):
    on_success = config.get("on_success", "")
    on_failure = config.get("on_failure", "")
    attachment = config.get("attachment", "html")

    on_success = on_success.split(",")
    on_failure = on_failure.split(",")

    on_success = list_to_emails(on_success)
    on_failure = list_to_emails(on_failure)

    return on_success, on_failure, attachment


def notify(config, is_success, error_msg, notebook_id, notebook_url):

    if not config:
        # no config provided, skip notify step
        return

    on_success, on_failure, attachment = parse_config(config)

    notebook_html_path = os.path.join(
        *(
            [settings.MEDIA_ROOT]
            + notebook_url.replace(settings.MEDIA_URL, "", 1).split("/")
        )
    )
    notebook_pdf_path = ""
    if "pdf" in attachment:
        export_to_pdf({"notebook_id": notebook_id, "notebook_path": notebook_url})
        notebook_pdf_path = notebook_html_path.replace(".html", ".pdf")

    email = None
    if on_success and is_success:
        msg = """Your notebook executed successfully"""
        email = EmailMessage(
            "Notebook executed successfully",
            msg,
            None,  # use default from email (from django settings)
            on_success,
        )
    if on_failure and not is_success:
        msg = """Your Notebook failed to execute"""
        email = EmailMessage(
            "Notebook failed to execute",
            msg,
            None,  # use default from email (from django settings)
            on_failure,
        )
    if email is not None:
        if "html" in attachment:
            email.attach_file(notebook_html_path)
        if "pdf" in attachment:
            email.attach_file(notebook_pdf_path)
        email.send(fail_silently=True)

