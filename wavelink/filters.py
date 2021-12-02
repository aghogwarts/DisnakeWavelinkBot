"""
The filter configurations are taken from Lavalink and pomice (Another Lavalink client), but rewritten entirely for
wavelink.
"""
from wavelink.errors import FilterInvalidArgument


class BaseFilter:
    """
    The base class for all filters.
    """

    def __init__(self, *, filter_name: str, payload: dict):
        self.payload = payload
        self.filter_name = filter_name

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.filter_name}> {self.payload}"

    def __str__(self):
        return self.filter_name

    @property
    def name(self):
        """
        The name of the filter.

        Returns
        -------
            The name of the filter.
        """
        return self.filter_name

    @classmethod
    def build_from_channel_mix(
            cls,
            left_to_right: float = 0.0,
            right_to_left: float = 0.0,
            right_to_right: float = 0.0,
            left_to_left: float = 0.0,
    ):
        """
        Filter which manually adjusts the panning of the audio, which can make
        for some cool effects when done correctly.

        Parameters
        ----------
        left_to_right : float
            The left to right panning.

        right_to_left : float
            The right to left panning.

        right_to_right : float
            The right to right panning.

        left_to_left : float
            The left to left panning.

        Returns
        -------
            The channel mix filter.
        """
        if 0 > left_to_left > 1:
            raise ValueError(
                "'left_to_left' value must be more than or equal to 0 or less than or equal to 1."
            )
        if 0 > right_to_right > 1:
            raise ValueError(
                "'right_to_right' value must be more than or equal to 0 or less than or equal to 1."
            )
        if 0 > left_to_right > 1:
            raise ValueError(
                "'left_to_right' value must be more than or equal to 0 or less than or equal to 1."
            )
        if 0 > right_to_left > 1:
            raise ValueError(
                "'right_to_left' value must be more than or equal to 0 or less than or equal to 1."
            )

        payload = {
            "channelMix": {
                "leftToLeft": left_to_left,
                "leftToRight": left_to_right,
                "rightToLeft": right_to_left,
                "rightToRight": right_to_right,
            }
        }
        return cls(filter_name="ChannelMix", payload=payload)

    @classmethod
    def build_from_distortion(
            cls,
            sin_offset: float = 0.0,
            sin_scale: float = 1.0,
            cos_offset: float = 0.0,
            cos_scale: float = 1.0,
            tan_offset: float = 0.0,
            tan_scale: float = 1.0,
            offset: float = 0.0,
            scale: float = 1.0,
    ):
        """
        Filter which produces a distortion effect.

        Parameters
        ----------
            The name of the filter.

        sin_offset : float
            The sin offset.

        sin_scale : float
            The sin scale.

        cos_offset : float
            The cos offset.

        cos_scale : float
            The cos scale.

        tan_offset : float
            The tan offset.

        tan_scale : float
            The tan scale.

        offset : float
            The offset.

        scale : float
            The scale.

        Returns
        -------
            The distortion filter.
        """

        payload = {
            "distortion": {
                "sinOffset": sin_offset,
                "sinScale": sin_scale,
                "cosOffset": cos_offset,
                "cosScale": cos_scale,
                "tanOffset": tan_offset,
                "tanScale": tan_scale,
                "offset": offset,
                "scale": scale,
            }
        }
        return cls(filter_name="Distortion", payload=payload)

    @classmethod
    def build_from_timescale(
            cls, speed: float = 1.0, pitch: float = 1.0, rate: float = 1.0
    ):
        """
        Filter which changes the speed and pitch of a track.
        You can make some very nice effects with this filter,

         Parameters
         ----------
         speed : float
             The speed.

         pitch : float
             The pitch.

         rate : float
             The rate.

         Returns
         -------
             The timescale filter.
        """
        if speed < 0:
            raise FilterInvalidArgument("Timescale speed must be more than 0.")
        if pitch < 0:
            raise FilterInvalidArgument("Timescale pitch must be more than 0.")
        if rate < 0:
            raise FilterInvalidArgument("Timescale rate must be more than 0.")

        payload = {
            "timescale": {
                "speed": speed,
                "pitch": pitch,
                "rate": rate
            }
        }
        return cls(filter_name="Timescale", payload=payload)

    @classmethod
    def karaoke(
            cls,
            *,
            level: float = 1.0,
            mono_level: float = 1.0,
            filter_band: float = 225.0,
            filter_width=100.0,
    ):
        """
        Build a karaoke filter.

        Parameters
        ----------
        level : float
            The level of the karaoke filter.

        mono_level : float
            The level of the karaoke filter when the channel is mono.

        filter_band : float
            The filter band of the karaoke filter.

        filter_width : float
            The filter width of the karaoke filter.

        Returns
        -------
            The karaoke filter.
        """

        payload = {
            "karaoke": {
                "level": level,
                "monoLevel": mono_level,
                "filterBand": filter_band,
                "filterWidth": filter_width,
            }
        }
        return cls(filter_name="Karaoke", payload=payload)

    @classmethod
    def tremolo(cls, *, frequency: float = 2.0, depth: float = 0.5):
        """
         Filter which produces a wavering tone in the music,
        causing it to sound like the music is changing in volume rapidly.

        Parameters
        ----------
        frequency : float
            The frequency of the vibrato.

        depth : float
            The depth of the vibrato.

        Returns
        -------
            The tremolo filter.
        """

        if frequency < 0:
            raise FilterInvalidArgument("Tremolo frequency must be more than 0.")
        if depth < 0 or depth > 1:
            raise FilterInvalidArgument("Tremolo depth must be between 0 and 1.")

        payload = {
            "tremolo":
            {
                "frequency":
                    frequency,
                "depth": depth
            }
        }
        return cls(filter_name="Tremolo", payload=payload)

    @classmethod
    def vibrato(cls, *, frequency: float = 2.0, depth: float = 0.5):
        """
         Filter which produces a wavering tone in the music,
         causing it to sound like the music is changing in pitch rapidly.

        Parameters
        ----------
        frequency : float
            The frequency of the vibrato.

        depth : float
            The depth of the vibrato.

        Returns
        -------
            The vibrato filter.
        """
        if frequency < 0 or frequency > 14:
            raise FilterInvalidArgument("Vibrato frequency must be between 0 and 14.")
        if depth < 0 or depth > 1:
            raise FilterInvalidArgument("Vibrato depth must be between 0 and 1.")

        payload = {
            "vibrato": {
                "frequency": frequency,
                "depth": depth
            }
        }
        return cls(filter_name="Vibrato", payload=payload)

    @classmethod
    def Eight_D_Audio(cls, *, rotation_hertz: float = 1.2):
        """
        Filter which produces a stereo-like panning effect, which sounds like
        the audio is being rotated around the listener's head.

        Parameters
        ----------
        rotation_hertz : float
            The rotation speed of the audio.

        Returns
        -------
            The 8D audio filter.
        """
        payload = {
            "8dAudio":
                {
                    "rotationHertz": rotation_hertz
                }
        }
        return cls(filter_name="8D Audio", payload=payload)
