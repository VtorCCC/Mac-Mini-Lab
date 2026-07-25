# 06 · Telegram setup

agent-hub messages you on Telegram when tasks report in or fail. You need two
values: a **bot token** and a **chat id**. This takes about 3 minutes.

> agent-hub runs fine without this — it just logs "Telegram not configured" and
> skips sending. Set it up whenever you're ready.

## Step 1 — create a bot and get the token

1. In Telegram, search for **@BotFather** (the official bot for making bots) and
   open a chat with it.
2. Send `/newbot`.
3. Follow the prompts: give it a name, then a username ending in `bot`.
4. BotFather replies with a **token** that looks like:

   ```
   123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
   ```

   That's your `TELEGRAM_BOT_TOKEN`. Keep it secret — anyone with it can control
   your bot.

## Step 2 — get your chat id

The bot can only message a chat it "knows about," so first **send your new bot a
message** (say "hi") from your own Telegram account. Then:

1. Open this URL in a browser, pasting in your token:

   ```
   https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates
   ```

   (Note the word `bot` stays right before your token.)

2. You'll get some JSON back. Look for `"chat":{"id":...}`. That number is your
   `TELEGRAM_CHAT_ID`. For a personal chat it's a positive number; for a group
   it's usually negative.

   If you see an empty result (`"result":[]`), send your bot another message and
   refresh the URL.

*(Alternative: message **@userinfobot**, which just replies with your id.)*

## Step 3 — put them in `config/.env`

If you haven't already, copy the template:

```bash
cp config/.env.example config/.env
```

Then edit `config/.env`:

```ini
TELEGRAM_BOT_TOKEN=123456789:AAExxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=987654321
```

No quotes needed. Save the file.

## Step 4 — test it

```bash
python main.py --test-telegram
```

You should get a "👋 Hello from agent-hub!" message. If not, see the
troubleshooting notes below.

## How it's used in the code

- `main.py` reads the two values from the environment (loaded from `.env`) and
  builds a `TelegramNotifier`.
- Any task can send a message with `self.ctx.notifier.send("your text")`.
- The notifier **never crashes** the app — a bad token or no network just logs a
  warning and returns `False`.

## Troubleshooting

| Symptom | Likely cause / fix |
|---------|--------------------|
| "Telegram not configured" warning | `config/.env` missing, or a value is blank. |
| Test says it couldn't send | Double-check the token; make sure you messaged the bot first. |
| `getUpdates` shows empty result | Send the bot a message, then refresh the URL. |
| Group messages not arriving | Add the bot to the group; the id is negative. |

## Security note

Your `.env` holds a secret. It's already listed in `.gitignore` so it won't be
committed to GitHub. Never paste your token into a public place. If it leaks,
send BotFather `/revoke` (or `/token`) to get a new one.
