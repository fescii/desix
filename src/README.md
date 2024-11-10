# Telegram and Twitter Bot Integration

This project integrates a Telegram bot with Twitter to monitor and manage Twitter accounts via Telegram commands. The bot allows users to request access, and admins to approve or deny access, promote users to admin, and manage monitored Twitter accounts.

## Features

- Start the bot and request access
- Admin commands to approve/deny users, promote/revoke admin status
- Add/remove Twitter accounts to monitor
- List all monitored Twitter accounts
- Help command to display available commands

## Requirements

- Python 3.12+
- FastAPI
- SQLAlchemy
- Telegram Bot API
- Tweepy (Twitter API)

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/fescii/desix.git
    cd desix
    ```

2. Create a virtual environment and activate it:
    ```sh
    python -m venv venv
    source venv/bin/activate
    ```

3. Install the required packages:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up the environment variables in a `.env` file:
    ```dotenv
    # Twitter API Configuration
    TWITTER_API_KEY=your_twitter_api_key
    TWITTER_API_SECRET=your_twitter_api_secret
    TWITTER_WEBHOOK_SECRET=your_webhook_secret
    TWITTER_BEARER_TOKEN=your_twitter_bearer_token
    TWITTER_ACCESS_SECRET=your_twitter_access_secret
    TWITTER_ACCESS_TOKEN=your_twitter_access_token

    # Telegram Bot Configuration
    TELEGRAM_TOKEN=your_telegram_token
    TELEGRAM_USERNAME=your_telegram_username

    # Admin Configuration
    SUPER_ADMIN_ID=your_super_admin_id

    # Application Configuration
    WEBHOOK_URL=https://your-domain.com/webhook

    # Database Configuration (optional, defaults to SQLite)
    DATABASE_URL=sqlite:///twitter_monitor.db
    ```

## Usage

1. Run the application:
    ```sh
    /path/to/venv/bin/python /path/to/yourproject/src/main.py
    ```

2. The application will start and the Telegram bot will be initialized. You can interact with the bot using the following commands:

### User Commands

- `/start` - Start the bot
- `/request_access` - Request access
- `/help` - Show help message

### Admin Commands

- `/approve_user <user_id>` - Approve a user
- `/deny_user <user_id>` - Deny a user
- `/promote_admin <user_id>` - Promote a user to admin
- `/revoke_admin <user_id>` - Revoke admin status
- `/add_account <@username>` - Add a Twitter account to monitor
- `/remove_account <username>` - Remove a monitored Twitter account
- `/list_accounts` - List all monitored accounts

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature-branch`)
3. Commit your changes (`git commit -am 'Add new feature'`)
4. Push to the branch (`git push origin feature-branch`)
5. Create a new Pull Request

## License

This project is licensed under the MIT License.