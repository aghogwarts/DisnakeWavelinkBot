import disnake
import wavelink
from bot_utils.MusicPlayerInteraction import Player


class Filter(disnake.ui.Select["FilterView"]):
    """
    Filter class for the FilterView.
    """

    def __init__(self, player: Player):
        self.player = player
        options = [
            disnake.SelectOption(
                label="Tremolo",
                description="Bass boost Filter.",
                emoji="🟥",
            ),
            disnake.SelectOption(
                label="Karaoke", description="Piano Filter.", emoji="🟩"
            ),
            disnake.SelectOption(label="8D", description="Metal Filter.", emoji="🟦"),
            disnake.SelectOption(
                label="Vibrato", description="Flat Filter.", emoji="🟨"
            ),
            disnake.SelectOption(
                label="ExtremeBass", description="ExtremeBass Filter.", emoji="🟩"
            ),
        ]

        super().__init__(
            placeholder="Choose your Filter...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: disnake.ApplicationCommandInteraction):
        """
        Callback for the Filter view.

        Parameters
        ----------
        interaction : disnake.ApplicationCommandInteraction
            The interaction object.

        Returns
        -------
        None
        """

        await interaction.response.send_message(f"Filter set to {self.values[0]}.")
        eqs = {
            "Tremolo": wavelink.BaseFilter.tremolo(),
            "Karaoke": wavelink.BaseFilter.karaoke(),
            "8D": wavelink.BaseFilter.Eight_D_Audio(),
            "Vibrato": wavelink.BaseFilter.vibrato(),
            "ExtremeBass": wavelink.BaseFilter.extreme_bass(),
        }  # you can make your own custom Filters and pass it here.
        await self.player.set_filter(eqs[self.values[0]])


class FilterView(disnake.ui.View):
    """
    A view that allows the user to set the filter.
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
