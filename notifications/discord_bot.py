"""Discord bot with scheduled knowledge cards and interactive Q&A."""

import asyncio
import json
import os
from pathlib import Path

import discord
import yaml
from discord.ext import commands, tasks

from .card_store import CardStore
from .claude_responder import ClaudeResponder
from .content_generator import ContentGenerator, MAX_DEEP_ANALYSIS_ROUNDS

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
        self.content_generator = ContentGenerator(self.store)

        # Channel → project mapping (reverse of config)
        self._channel_projects: dict[str, str] = {}
        channels = self.bot_config.get("channels", {})
        for project, channel_id in channels.items():
            self._channel_projects[str(channel_id)] = project

    async def setup_hook(self) -> None:
        """Called when bot is ready."""
        interval = self.bot_config["posting"].get("interval_hours", 4)
        self.post_knowledge_cards.change_interval(hours=interval)
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
        for channel_id, project in self._channel_projects.items():
            channel = self.get_channel(int(channel_id))
            if not channel or not isinstance(channel, discord.TextChannel):
                continue

            cards = self.store.get_unposted_cards(project, channel_id, limit=1)

            if not cards:
                # All cards exhausted — trigger deep analysis if rounds remain
                current_round = self.store.get_deep_analysis_round(project)
                if current_round < MAX_DEEP_ANALYSIS_ROUNDS:
                    await self._run_deep_analysis(project, channel)
                    # Try to get the newly generated cards
                    cards = self.store.get_unposted_cards(project, channel_id, limit=1)
                if not cards:
                    continue

            card = cards[0]
            embed = self._build_card_embed(card)
            msg = await channel.send(embed=embed)
            self.store.record_post(card["id"], channel_id, str(msg.id))

    async def _run_deep_analysis(self, project: str, channel: discord.TextChannel) -> None:
        """Run a deep analysis round: Opus generates analysis, Haiku creates cards."""
        current_round = self.store.get_deep_analysis_round(project)
        next_round = current_round + 1

        if next_round > MAX_DEEP_ANALYSIS_ROUNDS:
            return

        # Post status message
        status_embed = discord.Embed(
            title=f"Deep Analysis — Round {next_round}/{MAX_DEEP_ANALYSIS_ROUNDS}",
            description=(
                f"All factual cards for **{project}** have been posted. "
                f"Generating deeper insights... this may take a minute."
            ),
            color=discord.Color.from_rgb(255, 193, 7),  # Gold
        )
        await channel.send(embed=status_embed)

        # Run the CPU/API-heavy work in a thread to avoid blocking the event loop
        round_num, cards_count = await asyncio.to_thread(
            self.content_generator.run_deep_analysis, project
        )

        if round_num > 0 and cards_count > 0:
            result_embed = discord.Embed(
                title=f"Round {round_num} Analysis Complete",
                description=f"Generated **{cards_count}** new insight cards for **{project}**. Posting will resume shortly.",
                color=discord.Color.from_rgb(255, 193, 7),
            )
            await channel.send(embed=result_embed)

    @post_knowledge_cards.before_loop
    async def before_posting(self) -> None:
        await self.wait_until_ready()

    def _build_card_embed(self, card: dict) -> discord.Embed:
        """Build a Discord rich embed from a knowledge card."""
        tags = json.loads(card.get("tags", "[]")) if isinstance(card.get("tags"), str) else card.get("tags", [])

        is_insight = card.get("card_type") == "insight"

        if is_insight:
            color = discord.Color.from_rgb(255, 193, 7)  # Gold for insight cards
            # Extract round number from source_path (e.g. "deep_analysis/project_round2.md")
            round_label = ""
            source = card.get("source_path", "")
            if "round" in source:
                try:
                    round_num = source.split("round")[1].split(".")[0]
                    round_label = f"Deep Analysis · Round {round_num}"
                except (IndexError, ValueError):
                    round_label = "Deep Analysis"
            else:
                round_label = "Deep Analysis"
        else:
            color = discord.Color.from_rgb(63, 81, 181)  # Indigo for factual cards

        embed = discord.Embed(
            title=card["title"],
            description=card["summary"],
            color=color,
        )

        if is_insight and round_label:
            embed.add_field(name="Source", value=round_label, inline=True)

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
