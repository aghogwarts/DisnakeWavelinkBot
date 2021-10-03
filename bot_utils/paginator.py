from __future__ import annotations
import textwrap
import disnake
from bot_utils.menus import ListPageSource


class Paginator(ListPageSource):
    async def format_page(self, menu, embed: disnake.Embed):
        if len(menu.source.entries) != 1:
            em = embed.to_dict()
            if em.get("footer") is not None:
                if em.get("footer").get("text") is not None:
                    if not "Page: " in em.get("footer").get("text"):
                        em["footer"]["text"] = "".join(
                            f"{em['footer']['text']} • Page: {menu.current_page + 1}/{menu.source.get_max_pages()}" if
                            em['footer'][
                                "text"] is not None else f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}")
                    else:
                        em["footer"]["text"].replace(f"Page: {menu.current_page}/{menu.source.get_max_pages()}",
                                                     f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}")
            else:
                em["footer"] = {}
                em["footer"]["text"] = f"Page: {menu.current_page + 1}/{menu.source.get_max_pages()}"
            em = disnake.Embed().from_dict(em)
            return em
        return embed


class TextPaginator(ListPageSource):
    async def format_page(self, menu, text):
        return text


def WrapText(text: str, length: int):
    wrapper = textwrap.TextWrapper(width=length)
    words = wrapper.wrap(text=text)
    return words


def WrapList(list_: list, length: int):
    def chunks(seq, size):
        for i in range(0, len(seq), size):
            yield seq[i:i + size]

    return list(chunks(list_, length))
