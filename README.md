# Discord-Temporary-Mail
## A Discord Bot to setup your own Temporary Mail, inside of Discord.

First: 
1. Setup **config.json** - fill it with the Information. (Note: Domain is the @____ ) (The EMail Inbox whose details are filled must be a Catch All Inbox on that Domain)
2. Add the Bot to your server with Permissions: application.commands
3. Run the **bot.py** file
4. You should also see more .json files (these store information persistently).


Bot Information:
2 Commands: /temporarymail - makes an Alias for a Person and DMs the User that and its upcoming EMails. Aliases expire after 1 Day.
/summary - Statistics of the last 24 Hours, only usable by the Admin specified in config.json

The Bot also utilises IMAP IDLE for speed.
