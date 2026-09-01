# Railway setup

## Discord bot service
Use the same GitHub repository, but set this service's Start Command to:

python main.py

Add:
- DISCORD_TOKEN
- DISCORD_CLIENT_ID

## Website service
Create a second Railway service from the SAME GitHub repository.
Set its Root Directory to the repository root (or leave it blank).
Set its Start Command to:

python website.py

Railway will provide PORT automatically. Generate a public domain for this service.

Do not put Discord tokens or AI API keys in GitHub.
