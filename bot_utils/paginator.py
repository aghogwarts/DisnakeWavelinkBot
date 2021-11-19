from __future__ import annotations

import asyncio
import textwrap
from typing import List

import disnake
from bot_utils.menus import ListPageSource


class EmbedPaginator(disnake.ui.View):
    """
    A paginator that displays a list of items in an embed.
    """

    def __init__(
            self,
            ctx,
            embeds: List[disnake.Embed],
            *,
            timeout: float = 180.0,
            compact: bool = False,
    ):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.input_lock = asyncio.Lock()
        self.embeds = embeds
        self.current_page = 0
        self.compact: bool = compact

    def _update_labels(self, page_number: int) -> None:
        """
        Update the labels of the buttons to reflect the current page.
        :param page_number:
        :return:
        """
        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = len(self.embeds)
            self.go_to_last_page.disabled = (
                    max_pages is None or (page_number + 1) >= max_pages
            )
            self.go_to_next_page.disabled = (
                    max_pages is not None and (page_number + 1) >= max_pages
            )
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = len(self.embeds)
        if max_pages is not None:
            self.go_to_last_page.disabled = (page_number + 1) >= max_pages
            if (page_number + 1) >= max_pages:
                self.go_to_next_page.disabled = True
                self.go_to_next_page.label = "…"
            if page_number == 0:
                self.go_to_previous_page.disabled = True
                self.go_to_previous_page.label = "…"

    async def show_checked_page(
            self, interaction: disnake.Interaction, page_number: int
    ) -> None:
        """
        Show a page, but only if the interaction is valid.
        :param interaction:
        :param page_number:
        :return:
        """
        max_pages = len(self.embeds)
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction)
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        """
        Check if the interaction author is the author of the message.
        :param interaction:
        :return:
        """
        if interaction.user and interaction.user.id in (
                self.ctx.bot.owner_id,
                self.ctx.author.id,
        ):
            return True
        await interaction.response.send_message(
            "This pagination menu cannot be controlled by you, sorry!", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        """
        Called when the paginator times out.
        :return:
        """
        if self.message:
            await self.message.edit(view=None)

    async def show_page(self, page_number: int):
        """
        Show a page.
        :param page_number:
        :return:
        """
        if (page_number < 0) or (page_number > len(self.embeds) - 1):
            return
        self.current_page = page_number
        embed = self.embeds[page_number]
        embed.set_footer(text=f"Page {self.current_page + 1}/{len(self.embeds)}")
        await self.message.edit(embed=embed)

    @disnake.ui.button(label="≪", style=disnake.ButtonStyle.grey)
    async def go_to_first_page(
            self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """Go to the first page."""
        await self.show_page(0)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.blurple)
    async def go_to_previous_page(
            self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """Go to the previous page."""
        await self.show_page(self.current_page - 1)

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.blurple)
    async def go_to_next_page(
            self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """Go to the next page."""
        await self.show_page(self.current_page + 1)

    @disnake.ui.button(label="≫", style=disnake.ButtonStyle.grey)
    async def go_to_last_page(
            self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """Go to the last page."""
        await self.show_page(len(self.embeds) - 1)

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red)
    async def stop_pages(
            self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """stops the pagination session."""
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    async def start(self):
        """Start paginating over the embeds."""
        embed = self.embeds[0]
        embed.set_footer(text=f"Page 1/{len(self.embeds)}")
        self.message = await self.ctx.channel.send(embed=embed, view=self)


class SimpleEmbedPages(EmbedPaginator):
    """A simple pagination session."""

    def __init__(self, entries, *, ctx):
        super().__init__(embeds=entries, ctx=ctx)
        self.embed = disnake.Embed(colour=disnake.Colour.blurple())


class Paginator(ListPageSource):
    async def format_page(self, menu, embed: disnake.Embed):
        """
        Format the page.
        :param menu:
        :param embed:
        :return:
        """
        if len(menu.source.entries) != 1:
            em = embed.to_dict()
            if em.get("footer") is not None:
                if em.get("footer").get("text") is not None:
                    if not "Page: " in em.get("footer").get("text"):
                        em["footer"]["text"] = "".join(
                            f"{em['footer']['text']} • Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"
                            if em["footer"]["text"] is not None
                            else f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"
                        )
                    else:
                        em["footer"]["text"].replace(
                            f"Page: {menu.current_page}/{menu.source.get_max_pages()}",
                            f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}",
                        )
            else:
                em["footer"] = {}
                em["footer"][
                    "text"
                ] = f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"
            em = disnake.Embed().from_dict(em)
            return em
        return embed


class TextPaginator(ListPageSource):
    async def format_page(self, menu, text):
        """
        A paginator for text.
        :param menu:
        :param text:
        :return:
        """
        return text


def WrapText(text: str, length: int):
    """
    A function that wraps text.
    :param text:
    :param length:
    :return:
    """
    wrapper = textwrap.TextWrapper(width=length)
    words = wrapper.wrap(text=text)
    return words


def WrapList(list_: list, length: int):
    """
    A function that wraps a list.
    :param list_:
    :param length:
    :return:
    """

    def chunks(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i: i + size]

    return list(chunks(list_, length))
