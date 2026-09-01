
# Send bot — starter project

This project contains:
- `/dm` — DM a user
- `/send` — send to a text channel
- `/forum` — create a forum post
- `/invite` — show the bot invite button
- `/start talk code:<APP_CODE>` — activate a virtual talking app
- Black Send bot website with Discord OAuth dashboard
- Up to 10 virtual talking apps per Discord account
- App profile picture, name, description and generated `Name#1234` code
- Donation section with a GCash QR and a Discord Support link

## Important architecture note

The "Ahmand#2847" apps are **virtual characters inside the main Send bot**, not separate Discord bot accounts. Discord does not provide a normal public API for your bot to automatically create arbitrary new bot accounts. This project therefore keeps one real Discord bot and gives it multiple personalities.

Users can type `@Ahmand wassup` as text and Send bot replies as Ahmand. After `/start talk`, plain messages can also be sent to the active app.

## Setup

1. Create a Discord application/bot in the Discord Developer Portal.
2. Enable the **Message Content Intent** for the bot because the bot reads typed messages.
3. Put the bot token and OAuth credentials in environment variables. Never commit them.
4. For the website Discord login, add the callback URL:
   `https://YOUR-DOMAIN/callback`
5. Install dependencies:
   `pip install -r requirements.txt`
6. Start:
   `python main.py`

For a production host, run `python main.py` as the service command.

## AI

The talking feature uses the OpenAI Responses API. The API key belongs in `OPENAI_API_KEY`, not in GitHub. AI API usage can cost money.

## GitHub

GitHub can store this code, but GitHub Pages cannot run the Discord bot or the Flask dashboard backend. You still need a host to run `main.py`.

## Donation QR

`static/gcash_qr.png` is the QR-only crop supplied for this project. Replace it with a QR you control if necessary.
