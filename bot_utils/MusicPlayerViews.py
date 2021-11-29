import disnake

import wavelink
from wavelink import Player


class Equalizer(disnake.ui.Select["EqualizerView"]):
    """
    Equalizer view.
    """
    def __init__(self, player: Player):
        self.player = player
        options = [
            disnake.SelectOption(
                label="Boost",
                description="Bass boost equalizer.",
                emoji="🟥",
            ),
            disnake.SelectOption(
                label="Piano", description="Piano equalizer.", emoji="🟩"
            ),
            disnake.SelectOption(
                label="Metal", description="Metal equalizer.", emoji="🟦"
            ),
            disnake.SelectOption(
                label="Flat", description="Flat equalizer.", emoji="🟨"
            ),
        ]

        super().__init__(
            placeholder="Choose your equalizer...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Callback for the equalizer view.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The interaction object.

        Returns
        -------
        None
        """

        await interaction.response.send_message(f"Equalizer set to {self.values[0]}.")
        eqs = {
            "Flat": wavelink.Equalizer.flat(),
            "Boost": wavelink.Equalizer.boost(),
            "Metal": wavelink.Equalizer.metal(),
            "Piano": wavelink.Equalizer.piano(),
        }  # you can make your own custom equalizers and pass it here.
        await self.player.set_equalizer(eqs[self.values[0]])


class EqualizerView(disnake.ui.View):
    """
    Equalizer view.
    """
    def __init__(
        self, interaction: disnake.ApplicationCommandInteraction, player: Player
    ):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.add_item(Equalizer(player=player))

    async def interaction_check(
        self, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        Check if the interaction is the same as the one that created this view.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The interaction to check.

        Returns
        -------
        None
        """
        if interaction.author.id != self.interaction.author.id:
            return await interaction.response.send_message(
                "This is not your menu!", ephemeral=True
            )
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_message(view=self)


class Filter(disnake.ui.Select["FilterView"]):
    """
    Filter view.
    """
    def __init__(self, player: Player):
        self.player = player
        # Set the options that will be presented inside the dropdown
        options = [
            disnake.SelectOption(
                label="Tremolo",
                description="Tremolo filter.",
                emoji="🟥",
            ),
            disnake.SelectOption(
                label="Karaoke", description="Karaoke filter.", emoji="🟩"
            ),
            disnake.SelectOption(
                label="Vibrato", description="Vibrato filter.", emoji="🟦"
            ),
            disnake.SelectOption(label="8D", description="8D audio filter.", emoji="🟨"),
        ]

        super().__init__(
            placeholder="Choose your filter...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Callback for the filter view.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The interaction object.

        Returns
        -------
        None
        """

        await interaction.response.send_message(f"Filter set to {self.values[0]}.")
        filters = {
            "Tremolo": wavelink.BaseFilter.tremolo(),
            "Karaoke": wavelink.BaseFilter.karaoke(),
            "Vibrato": wavelink.BaseFilter.vibrato(),
            "8D": wavelink.BaseFilter.Eight_D_Audio(),
        }
        # you can make your own custom filters and pass it here.
        await self.player.set_filter(filters[self.values[0]])


class FilterView(disnake.ui.View):
    """
    Filter view.
    """
    def __init__(
        self, interaction: disnake.ApplicationCommandInteraction, player: Player
    ):
        super().__init__(timeout=60)
        self.interaction = interaction
        self.add_item(Filter(player=player))

    async def interaction_check(
        self, interaction: disnake.ApplicationCommandInteraction
    ):
        """
        Check if the user who is using the menu is the same as the user who invoked the menu.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The interaction to check.

        Returns
        -------
        None
        """
        if interaction.author.id != self.interaction.author.id:
            return await interaction.response.send_message(
                "This is not your menu!", ephemeral=True
            )

    async def on_timeout(self) -> None:
        """
        Called when the menu times out.

        Returns
        -------
        None
        """
        for item in self.children:
            item.disabled = True
        await self.interaction.edit_original_message(view=self)
