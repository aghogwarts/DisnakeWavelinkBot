#  -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
import textwrap
import typing
from typing import List

import disnake

from utils import menus
from utils.menus import ListPageSource


class ViewPages(disnake.ui.View):
    """
    A view paginator that can be used to display a list of items in embeds as pages.
    """

    def __init__(
        self,
        source: menus.PageSource,
        *,
        ctx: disnake.ApplicationCommandInteraction,
        check_embeds: bool = True,
        compact: bool = False,
    ):
        super().__init__()
        self.source: menus.PageSource = source
        self.check_embeds: bool = check_embeds
        self.ctx: disnake.ApplicationCommandInteraction = ctx
        self.message: typing.Optional[disnake.Message] = None
        self.current_page: int = 0
        self.compact: bool = compact
        self.input_lock = asyncio.Lock()
        self.clear_items()
        self.fill_items()

    def fill_items(self) -> None:
        """
        Fills the items with the items from the source.
        """
        if not self.compact:
            self.stop_pages.row = 1

        if self.source.is_paginating():
            max_pages = self.source.get_max_pages()
            use_last_and_first = max_pages is not None and max_pages >= 2
            if use_last_and_first:
                self.add_item(self.go_to_first_page)  # type: ignore
            self.add_item(self.go_to_previous_page)   # type: ignore
            if not self.compact:
                self.add_item(self.go_to_current_page)  # type: ignore
            self.add_item(self.go_to_next_page)  # type: ignore
            if use_last_and_first:
                self.add_item(self.go_to_last_page)  # type: ignore
            self.add_item(self.stop_pages)  # type: ignore

    async def _get_kwargs_from_page(self, page: int) -> typing.Dict[str, typing.Any]:
        """
        Gets the keyword arguments from a page (embed).


        Parameters
        ----------
        page : int
            The page (embed) to get the keyword arguments from.
        """
        value = await disnake.utils.maybe_coroutine(self.source.format_page, self, page)
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            return {"content": value, "embed": None}
        elif isinstance(value, disnake.Embed):
            return {"embed": value, "content": None}
        else:
            return {}

    async def show_page(
        self, interaction: disnake.Interaction, page_number: int
    ) -> None:
        """
        Shows the page with the given number.


        Parameters
        ----------
        interaction : disnake.Interaction
            The interaction that triggered this page.

        page_number : int
            The page number to show.
        """
        page = await self.source.get_page(page_number)
        self.current_page = page_number
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(page_number)
        if kwargs:
            if interaction.response.is_done():
                if self.message:
                    await self.message.edit(**kwargs, view=self)
            else:
                await interaction.response.edit_message(**kwargs, view=self)

    def _update_labels(self, page_number: int) -> None:
        """
        Updates the labels of the numbered page button.

        Parameters
        ----------
        page_number : int
            The page number to update the label of.
        """
        self.go_to_first_page.disabled = page_number == 0
        if self.compact:
            max_pages = self.source.get_max_pages()
            self.go_to_last_page.disabled = (
                max_pages is None or (page_number + 1) >= max_pages
            )
            self.go_to_next_page.disabled = (
                max_pages is not None and (page_number + 1) >= max_pages
            )
            self.go_to_previous_page.disabled = page_number == 0
            return

        self.go_to_current_page.label = str(page_number + 1)
        self.go_to_previous_page.label = str(page_number)
        self.go_to_next_page.label = str(page_number + 2)
        self.go_to_next_page.disabled = False
        self.go_to_previous_page.disabled = False
        self.go_to_first_page.disabled = False

        max_pages = self.source.get_max_pages()
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
        Shows the page with the given number.
        """
        max_pages = self.source.get_max_pages()
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction, page_number)
            elif max_pages > page_number >= 0:
                await self.show_page(interaction, page_number)
        except IndexError:
            # If an Index Error happens, it has been handled, so it can be ignored.
            pass

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        if interaction.user and interaction.user.id in (
            self.ctx.bot.owner_id,
            self.ctx.author.id,
        ):
            return True
        await interaction.response.send_message(
            "This is not your menu.", ephemeral=True
        )
        return False

    async def on_timeout(self) -> None:
        if self.message:
            await self.message.edit(view=None)

    async def on_error(
        self, error: Exception, item: disnake.ui.Item, interaction: disnake.Interaction
    ) -> None:
        safe_send = (
            interaction.response.followup
            if interaction.response.is_done()
            else interaction.response.send_message
        )
        await safe_send(
            "An error occurred while trying to show this page.", ephemeral=True
        )

    async def start(self) -> None:
        """
        Starts the pagination menu.
        """
        if (
            self.check_embeds
            and not self.ctx.channel.permissions_for(self.ctx.me).embed_links
        ):
            await self.ctx.send(
                "Bot does not have embed links permission in this channel."
            )
            return

        await self.source._prepare_once()  # type: ignore
        page = await self.source.get_page(0)
        kwargs = await self._get_kwargs_from_page(page)
        self._update_labels(0)
        self.message = await self.ctx.send(**kwargs, view=self)

    @disnake.ui.button(label="≪", style=disnake.ButtonStyle.grey)
    async def go_to_first_page(
        self, _: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        A button to go to the first page.
        """
        await self.show_page(interaction, 0)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.blurple)
    async def go_to_previous_page(
        self, _: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        A button to go to the previous page.
        """
        await self.show_checked_page(interaction, self.current_page - 1)

    @disnake.ui.button(label="Current", style=disnake.ButtonStyle.grey, disabled=True)
    async def go_to_current_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        pass

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.blurple)
    async def go_to_next_page(
        self, _: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        A button that goes to the next page.

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed. (Unused)

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        await self.show_checked_page(interaction, self.current_page + 1)

    @disnake.ui.button(label="≫", style=disnake.ButtonStyle.grey)
    async def go_to_last_page(
        self, _: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        A button to go to the last page.

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed. (Unused)

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        # The call here is safe because it's guarded by skip_if
        await self.show_page(interaction, self.source.get_max_pages() - 1)

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red)
    async def stop_pages(
        self, _: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        Stops the pagination session.

        Parameters
        ----------
        _ : disnake.ui.Button
            The button that was pressed. (Unused)

        interaction : disnake.Interaction
        """
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()


class RichPager(menus.ListPageSource):
    """
    A class that formats the page (embed) to add more information.
    """

    async def format_page(self, menu, entries):
        pages = []
        for index, entry in enumerate(entries, start=menu.current_page * self.per_page):  # type: ignore
            pages.append(f"{index + 1}. {entry}")

        maximum = self.get_max_pages()
        if maximum > 1:
            footer = (
                f"Page {menu.current_page + 1}/{maximum} ({len(self.entries)} entries)"  # type: ignore
            )
            menu.embed.set_footer(text=footer)  # type: ignore

        menu.embed.description = "\n".join(pages)  # type: ignore
        return menu.embed  # type: ignore


class EmbedPaginator(disnake.ui.View):
    """
    A paginator that displays a list of embeds.
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
        self.message = None
        self.ctx = ctx
        self.input_lock = asyncio.Lock()
        self.embeds = embeds
        self.current_page = 0
        self.compact: bool = compact

    def _update_labels(self, page_number: int) -> None:
        """
        Update the labels of the buttons to reflect the current page.

        Parameters
        ----------
        page_number : int
            The current page number.
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

        Parameters
        ----------
        interaction : disnake.Interaction
            The interaction to check.

        page_number : int
            The page number to show.
        """
        max_pages = len(self.embeds)
        try:
            if max_pages is None:
                # If it doesn't give maximum pages, it cannot be checked
                await self.show_page(interaction)  # type: ignore
            elif max_pages > page_number >= 0:
                await self.show_page(interaction)  # type: ignore
        except IndexError:
            # An error happened that can be handled, so ignore it.
            pass

    async def interaction_check(self, interaction: disnake.Interaction) -> bool:
        """
        Check if the interaction author is the author of the message.

        Parameters
        ----------
        interaction : disnake.Interaction
            The interaction to check.

        Returns
        -------
        bool
            Whether the interaction author is the author of the message.
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

        Returns
        -------
        None
        """
        if self.message:
            await self.message.edit(view=None)

    async def show_page(self, page_number: int):
        """
        Show a page.

        Parameters
        ----------
        page_number : int
            The page number to show.
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
        """
        Go to the first page.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        await interaction.response.defer()
        await self.show_page(0)

    @disnake.ui.button(label="Back", style=disnake.ButtonStyle.blurple)
    async def go_to_previous_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        Go to the previous page.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        await interaction.response.defer()
        await self.show_page(self.current_page - 1)

    @disnake.ui.button(label="Next", style=disnake.ButtonStyle.blurple)
    async def go_to_next_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        Go to the next page.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        await interaction.response.defer()
        await self.show_page(self.current_page + 1)

    @disnake.ui.button(label="≫", style=disnake.ButtonStyle.grey)
    async def go_to_last_page(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        Go to the last page.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        await interaction.response.defer()
        await self.show_page(len(self.embeds) - 1)

    @disnake.ui.button(label="Quit", style=disnake.ButtonStyle.red)
    async def stop_pages(
        self, button: disnake.ui.Button, interaction: disnake.Interaction
    ):
        """
        Stops the pagination session.

        Parameters
        ----------
        button : disnake.ui.Button
            The button that was pressed.

        interaction : disnake.Interaction
            The interaction that was performed.
        """
        await interaction.response.defer()
        await interaction.delete_original_message()
        self.stop()

    async def start(self):
        """
        Start paginating over the embeds.
        """
        embed = self.embeds[0]
        embed.set_footer(text=f"Page 1/{len(self.embeds)}")
        self.message = await self.ctx.edit_original_message(embed=embed, view=self)


class SimpleEmbedPages(EmbedPaginator):
    """
    A simple pagination session.

    Parameters
    ----------
    ctx : disnake.ApplicationCommandInteraction
        The context of the message.

    entries : list
        A list of embeds to paginate over.
    """

    def __init__(self, entries, *, ctx):
        super().__init__(embeds=entries, ctx=ctx)
        self.embed = disnake.Embed(colour=disnake.Colour.blurple())


class Paginator(ListPageSource):
    """
    A paginator for a list of entries.
    """

    async def format_page(self, menu, embed: disnake.Embed) -> disnake.Embed:
        """
        A method that formats the page.

        Parameters
        ----------
        menu : menus.Menu
            The menu that is being paginated.
        embed : disnake.Embed
            The embed that is being paginated.

        Returns
        -------
        disnake.Embed
            The formatted embed.
        """
        if len(menu.source.entries) != 1:  # type: ignore
            em = embed.to_dict()
            if em.get("footer") is not None:
                if em.get("footer").get("text") is not None:
                    if "Page: " not in em.get("footer").get("text"):
                        em["footer"]["text"] = "".join(
                            f"{em['footer']['text']} • Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"  # type: ignore
                            if em["footer"]["text"] is not None
                            else f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"  # type: ignore
                        )
                    else:
                        em["footer"]["text"].replace(
                            f"Page: {menu.current_page}/{menu.source.get_max_pages()}",  # type: ignore
                            f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}",  # type: ignore
                        )
            else:
                em["footer"] = {}  # type: ignore
                em["footer"][
                    "text"
                ] = f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"  # type: ignore
            em = disnake.Embed().from_dict(em)
            return em
        return embed


class TextPaginator(ListPageSource):
    """
    A paginator for text.
    """

    async def format_page(self, menu, text: str) -> str:
        """
        Format the page.

        Parameters
        ----------
        menu : menus.Menu
            The menu.
        text : str
            The text.

        Returns
        -------
        str
            The formatted text.
        """
        return text


def WrapText(text: str, length: int) -> typing.List[str]:
    """
    A function that wraps text.

    Parameters
    ----------
    text : str
        The text to wrap.
    length : int
        The length to wrap the text at.

    Returns
    -------
    typing.List[str]
        A list of strings.
    """
    wrapper = textwrap.TextWrapper(width=length)
    words = wrapper.wrap(text=text)
    return words


def WrapList(list_: list, length: int) -> typing.List[list]:
    """
    A function that wraps a list.

    Parameters
    ----------
    list_ : list
        The list to be wrapped.
    length : int
        The length of the list.

    Returns
    -------
    list
        The wrapped list.
    """

    def chunks(seq: list, size: int) -> list:
        """
        A function that splits a list into chunks.

        Parameters
        ----------
        seq : list
            The list to split.

        size : int
            The size of the chunks.

        Returns
        -------
        list
            The list of chunks.
        """
        for i in range(0, len(seq), size):
            yield seq[i: i + size]

    return list(chunks(list_, length))
