import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from threading import Thread
from dotenv import load_dotenv

load_dotenv()


class EmailNotifier:
    def __init__(self):
        self.sender_email = os.getenv("SMTP_USER", "")
        self.sender_password = os.getenv("SMTP_PASSWORD", "")

        email_lower = self.sender_email.lower()
        if "gmail.com" in email_lower:
            self.smtp_server = "smtp.gmail.com"
            self.smtp_port = 587
        elif "yandex.ru" in email_lower or "ya.ru" in email_lower:
            self.smtp_server = "smtp.yandex.ru"
            self.smtp_port = 465
        else:
            self.smtp_server = "smtp.yandex.ru"
            self.smtp_port = 465

    def send_alert_async(self, recipient_email, plate, address, time_str, date_str):
        """Отправка уведомления асинхронно"""
        if not self.sender_email or not self.sender_password:
            print("⚠️ SMTP не настроен (SMTP_USER/SMTP_PASSWORD пустые) — письмо не отправлено")
            return
        if not recipient_email or "@" not in recipient_email:
            print(f"⚠️ Ошибка: Некорректный адрес получателя '{recipient_email}'")
            return

        thread = Thread(
            target=self._send_email,
            args=(recipient_email, plate, address, time_str, date_str)
        )
        thread.daemon = True
        thread.start()

    def _send_email(self, recipient_email, plate, address, time_str, date_str):
        """Отправка email (выполняется в отдельном потоке)"""
        maps_link = f"https://www.google.com/maps/search/?api=1&query={address.replace(' ', '+')}"

        subject = f"🚨 РОЗЫСК: Обнаружен автомобиль {plate}"

        html_body = f"""
        <html>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; color: #333; line-height: 1.5;">
            <div style="max-width: 500px; margin: auto; border: 2px solid #d32f2f; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
                <div style="background-color: #d32f2f; color: white; padding: 20px; text-align: center;">
                    <h2 style="margin: 0; text-transform: uppercase; letter-spacing: 1px;">Внимание! Обнаружен розыск</h2>
                </div>
                <div style="padding: 25px; background-color: #ffffff;">
                    <p style="margin-top: 0; font-size: 16px;">Системой фиксации ГИБДД обнаружено транспортное средство:</p>
                    <div style="background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #d32f2f; margin: 20px 0;">
                        <p style="margin: 5px 0;"><b>Гос. номер (ГРЗ):</b> <span style="font-size: 18px; color: #d32f2f;">{plate}</span></p>
                        <p style="margin: 5px 0;"><b>Место фиксации:</b> {address}</p>
                        <p style="margin: 5px 0;"><b>Время:</b> {time_str}</p>
                        <p style="margin: 5px 0;"><b>Дата:</b> {date_str}</p>
                    </div>
                    <div style="text-align: center; margin: 30px 0 10px 0;">
                        <a href="{maps_link}" 
                           style="background-color: #1976d2; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; font-weight: bold; display: inline-block; box-shadow: 0 2px 4px rgba(0,0,0,0.2);">
                           📍 ПОКАЗАТЬ НА КАРТЕ
                        </a>
                    </div>
                    <p style="margin-top: 25px; font-size: 12px; color: #888; text-align: center; border-top: 1px solid #eee; padding-top: 15px;">
                        Данное сообщение сформировано автоматически.<br>Система оперативного розыска ГИБДД КИРОВ.
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = f"ГИБДД КИРОВ <{self.sender_email}>"
        msg['To'] = recipient_email

        plain_body = f"ВНИМАНИЕ! Обнаружен ГРЗ: {plate}\nМесто: {address}\nВремя: {time_str}\nДата: {date_str}"
        msg.attach(MIMEText(plain_body, 'plain', 'utf-8'))
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

        try:
            if self.smtp_port == 587:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=20)
                server.ehlo()
                server.starttls()
                server.ehlo()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=20)

            server.login(self.sender_email, self.sender_password)
            server.sendmail(self.sender_email, [recipient_email], msg.as_string())
            server.quit()
            print(f"✅ Email отправлен на {recipient_email} для {plate}")

        except Exception as e:
            print(f"❌ Ошибка отправки email: {e}")