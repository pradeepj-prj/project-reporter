"""Discord bot with scheduled knowledge cards and interactive Q&A."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import discord
import yaml
from discord.ext import commands, tasks

from .card_store import CardStore
from .claude_responder import ClaudeResponder

CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "discord.yaml"
PROJECTS_CONFIG = Path(__file__).resolve().parent.parent / "config" / "projects.yaml"


class ProjectReporterBot(commands.Bot):
    """Discord bot that posts knowledge cards and answers questions."""

    def __init__(self):
        self.bot_config = yaml.safe_load(CONFIG_PATH.read_text())
        self.projects_config = yaml.safe_load(PROJECTS_CONFIG.read_text())

        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(
            command_prefix=self.bot_config["bot"]["command_prefix"],
            intents=intents,
        )

        self.store = CardStore()
        self.responder = ClaudeResponder()

        # Channel → project mapping (reverse of config)
        self._channel_projects: dict[str, str] = {}
        channels = self.bot_config.get("channels", {})
        for project, channel_id in channels.items():
            self._channel_projects[str(channel_id)] = project

    async def setup_hook(self) -> None:
        """Called when bot is ready."""
        self.post_knowledge_cards.start()

    async def on_ready(self) -> None:
        print(f"Bot connected as {self.user}")
        print(f"Watching {len(self._channel_projects)} channels")

    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.user:
            return

        # Handle threaded replies for Q&A
        if isinstance(message.channel, discord.Thread):
            await self._handle_thread_message(message)
            return

        # Handle reactions
        await self.process_commands(message)

    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Handle reactions on knowledge cards."""
        if payload.user_id == self.user.id:  # type: ignore[union-attr]
            return

        channel = self.get_channel(payload.channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        emoji = str(payload.emoji)
        explain_emoji = self.bot_config["reactions"]["explain_more"]

        if emoji == explain_emoji:
            # Create thread and explain more
            message = await channel.fetch_message(payload.message_id)
            if message.author == self.user:
                thread = await message.create_thread(name=f"Deep dive: {message.embeds[0].title if message.embeds else 'topic'}")
                project = self._channel_projects.get(str(channel.id))
                question = f"Explain more about: {message.embeds[0].title if message.embeds else message.content[:100]}"
                response = self.responder.respond(question, project=project)
                await thread.send(response)

    async def _handle_thread_message(self, message: discord.Message) -> None:
        """Handle a message in a thread — run Q&A."""
        thread = message.channel
        assert isinstance(thread, discord.Thread)

        # Determine project from parent channel
        parent_id = str(thread.parent_id) if thread.parent_id else ""
        project = self._channel_projects.get(parent_id)

        # Build thread history
        history: list[dict[str, str]] = []
        async for msg in thread.history(limit=50, oldest_first=True):
            if msg.id == message.id:
                break
            role = "assistant" if msg.author == self.user else "user"
            history.append({"role": role, "content": msg.content})

        async with message.channel.typing():
            response = self.responder.respond(
                message.content,
                project=project,
                thread_history=history,
            )

        await message.reply(response)

    @tasks.loop(hours=4)
    async def post_knowledge_cards(self) -> None:
        """Post a knowledge card to each project channel on schedule."""
        config = self.bot_config["posting"]
        now = datetime.now(timezone.utc)

        # Respect quiet hours
        if config["quiet_hours_start"] <= now.hour or now.hour < config["quiet_hours_end"]:
            return

        for channel_id, project in self._channel_projects.items():
            channel = self.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            cards = self.store.get_unposted_cards(project, channel_id, limit=1)
            if not cards:
                continue

            card = cards[0]
            embed = self._build_card_embed(card)
            msg = await channel.send(embed=embed)

            # Add reaction buttons
            await msg.add_reaction(self.bot_config["reactions"]["got_it"])
            await msg.add_reaction(self.bot_config["reactions"]["explain_more"])

            self.store.record_post(card["id"], channel_id, str(msg.id))

    @post_knowledge_cards.before_loop
    async def before_posting(self) -> None:
        await self.wait_until_ready()

    def _build_card_embed(self, card: dict) -> discord.Embed:
        """Build a Discord rich embed from a knowledge card."""
        tags = json.loads(card.get("tags", "[]")) if isinstance(card.get("tags"), str) else card.get("tags", [])

        embed = discord.Embed(
            title=card["title"],
            description=card["summary"],
            color=discord.Color.from_rgb(63, 81, 181),  # Indigo
        )

        if card.get("insight"):
            embed.add_field(name="Key Insight", value=card["insight"], inline=False)

        if tags:
            embed.add_field(name="Tags", value=" · ".join(f"`{t}`" for t in tags), inline=False)

        if card.get("source_url"):
            embed.add_field(name="Full Article", value=card["source_url"], inline=False)

        embed.set_footer(text=f"Project: {card['project']}")
        return embed


def run_bot() -> None:
    """Entry point for running the Discord bot."""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is required")

    bot = ProjectReporterBot()
    bot.run(token)


if __name__ == "__main__":
    run_bot()
