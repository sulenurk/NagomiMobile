from __future__ import annotations

from kivy.utils import get_color_from_hex


THEME_PALETTES = {
    "purple": {
        "name": "Purple",
        "primary": "#6D5DF6", "primary_hover": "#5B4EE6", "primary_soft": "#312E81",
        "dark": {"bg": "#020617", "sidebar": "#030712", "surface": "#0F172A", "surface_light": "#111827", "card": "#111827", "card_soft": "#1E293B", "card_border": "#1F2937", "text": "#F8FAFC", "muted": "#94A3B8", "soft": "#CBD5E1", "input": "#EDE9FE", "input_text": "#111827"},
        "light": {"bg": "#F6F4FF", "sidebar": "#EEEAFE", "surface": "#F8F7FD", "surface_light": "#F0EDFC", "card": "#FFFFFF", "card_soft": "#E4DFFD", "card_border": "#CFC6F5", "text": "#1E1B4B", "muted": "#64748B", "soft": "#475569", "input": "#FFFFFF", "input_text": "#1E1B4B"},
    },
    "pinky": {
        "name": "Pinky", "primary": "#D977A8", "primary_hover": "#BE5D91", "primary_soft": "#6B314E",
        "dark": {"bg": "#151016", "sidebar": "#1B121B", "surface": "#251B27", "surface_light": "#2D202E", "card": "#251B27", "card_soft": "#3A293B", "card_border": "#493547", "text": "#FFF7FC", "muted": "#C6AEBB", "soft": "#E8D6DF", "input": "#FCE7F3", "input_text": "#3B1028"},
        "light": {"bg": "#FFF6FA", "sidebar": "#FBE8F1", "surface": "#FFF9FC", "surface_light": "#FCEBF3", "card": "#FFFFFF", "card_soft": "#F5D4E4", "card_border": "#EAB7D0", "text": "#4A1834", "muted": "#806273", "soft": "#5E3D50", "input": "#FFFFFF", "input_text": "#4A1834"},
    },
    "ocean": {
        "name": "Ocean Blue", "primary": "#0E89C9", "primary_hover": "#0874AE", "primary_soft": "#0B4265",
        "dark": {"bg": "#06141D", "sidebar": "#071B27", "surface": "#0C2533", "surface_light": "#102D3D", "card": "#0C2533", "card_soft": "#173B4D", "card_border": "#21495C", "text": "#F0FAFF", "muted": "#9DB9C7", "soft": "#C8DEE8", "input": "#E0F2FE", "input_text": "#0C3147"},
        "light": {"bg": "#F2FAFE", "sidebar": "#E0F2FC", "surface": "#F7FCFF", "surface_light": "#E9F7FE", "card": "#FFFFFF", "card_soft": "#CBEAF9", "card_border": "#A7D8F0", "text": "#12344A", "muted": "#5B7D91", "soft": "#35586B", "input": "#FFFFFF", "input_text": "#12344A"},
    },
    "forest": {
        "name": "Forest Green", "primary": "#16A36A", "primary_hover": "#108554", "primary_soft": "#0B4A32",
        "dark": {"bg": "#071711", "sidebar": "#091D15", "surface": "#10271C", "surface_light": "#153021", "card": "#10271C", "card_soft": "#20402E", "card_border": "#315443", "text": "#F2FFF8", "muted": "#ABC8B8", "soft": "#D0E5D9", "input": "#DCFCE7", "input_text": "#123D29"},
        "light": {"bg": "#F2FAF5", "sidebar": "#E2F3E9", "surface": "#F7FDF9", "surface_light": "#EAF7EF", "card": "#FFFFFF", "card_soft": "#D1ECD9", "card_border": "#AED9BD", "text": "#173C29", "muted": "#648574", "soft": "#385B49", "input": "#FFFFFF", "input_text": "#173C29"},
    },
    "monochrome": {
    "name": "Monochrome",

    "primary": "#5E5E5E",
    "primary_hover": "#474747",
    "primary_soft": "#2D2D2D",

    "dark": {
        "bg": "#0A0A0A",
        "sidebar": "#111111",
        "surface": "#171717",
        "surface_light": "#1F1F1F",
        "card": "#1A1A1A",
        "card_soft": "#252525",
        "card_border": "#333333",
        "text": "#FFFFFF",
        "muted": "#9E9E9E",
        "soft": "#D8D8D8",
        "input": "#2B2B2B",
        "input_text": "#FFFFFF"
    },

    "light": {
        "bg": "#F8F8F8",
        "sidebar": "#ECECEC",
        "surface": "#FFFFFF",
        "surface_light": "#F3F3F3",
        "card": "#FFFFFF",
        "card_soft": "#E4E4E4",
        "card_border": "#CCCCCC",
        "text": "#1C1C1C",
        "muted": "#777777",
        "soft": "#555555",
        "input": "#FFFFFF",
        "input_text": "#1C1C1C"
    }
},
    "slate": {
    "name": "Slate",

    "primary": "#64748B",
    "primary_hover": "#475569",
    "primary_soft": "#334155",

    "dark": {
        "bg": "#0F172A",
        "sidebar": "#111827",
        "surface": "#1E293B",
        "surface_light": "#243447",
        "card": "#1E293B",
        "card_soft": "#334155",
        "card_border": "#475569",
        "text": "#F8FAFC",
        "muted": "#94A3B8",
        "soft": "#CBD5E1",
        "input": "#E2E8F0",
        "input_text": "#1E293B"
    },

    "light": {
        "bg": "#F8FAFC",
        "sidebar": "#EEF2F7",
        "surface": "#FFFFFF",
        "surface_light": "#F3F6FA",
        "card": "#FFFFFF",
        "card_soft": "#E2E8F0",
        "card_border": "#CBD5E1",
        "text": "#1E293B",
        "muted": "#64748B",
        "soft": "#475569",
        "input": "#FFFFFF",
        "input_text": "#1E293B"
    }
},
"amber": {
        "name": "Sunset Amber",
        "primary": "#D97706", "primary_hover": "#B45309", "primary_soft": "#78350F",
        "dark": {
            "bg": "#140E0A", "sidebar": "#1A120C", "surface": "#221810", "surface_light": "#2C1F15", 
            "card": "#221810", "card_soft": "#36261B", "card_border": "#463223", "text": "#FEF3C7", 
            "muted": "#C2A894", "soft": "#EAD5C3", "input": "#FEF3C7", "input_text": "#451A03"
        },
        "light": {
            "bg": "#FFFBEB", "sidebar": "#FEF3C7", "surface": "#FFFDF5", "surface_light": "#FDF6E2", 
            "card": "#FFFFFF", "card_soft": "#FDE68A", "card_border": "#FCD34D", "text": "#451A03", 
            "muted": "#785841", "soft": "#593F2B", "input": "#FFFFFF", "input_text": "#451A03"
        }
    },
    "mint": {
        "name": "Nordic Mint",
        "primary": "#0D9488", "primary_hover": "#0F766E", "primary_soft": "#115E59",
        "dark": {
            "bg": "#0B0F12", "sidebar": "#0E141B", "surface": "#121B22", "surface_light": "#1A242F", 
            "card": "#121B22", "card_soft": "#1E2D3B", "card_border": "#24374A", "text": "#E2F1F1", 
            "muted": "#7FA3A1", "soft": "#A9C7C5", "input": "#CCFBF1", "input_text": "#115E59"
        },
        "light": {
            "bg": "#F0F9F9", "sidebar": "#E0F2F1", "surface": "#F4FBFB", "surface_light": "#E5F5F5", 
            "card": "#FFFFFF", "card_soft": "#CDEBE9", "card_border": "#B2DFDB", "text": "#0F3231", 
            "muted": "#547573", "soft": "#3A5251", "input": "#FFFFFF", "input_text": "#0F3231"
        }
    },
}

PALETTE_NAMES = {
    "purple": "Purple",
    "pinky": "Pinky",
    "ocean": "Ocean Blue",
    "forest": "Forest Green",
    "monochrome": "Monochrome",
    "slate": "Slate",
    "amber": "Sunset Amber",
    "mint": "Nordic Mint",
}


def hex_to_rgba(hex_color: str) -> list[float]:
    return list(get_color_from_hex(hex_color))


def build_theme(
    palette_key: str = "purple",
    appearance_mode: str = "dark",
) -> dict[str, list[float]]:
    palette = THEME_PALETTES.get(
        palette_key,
        THEME_PALETTES["purple"],
    )

    mode = (
        "light"
        if appearance_mode == "light"
        else "dark"
    )

    mode_colors = palette[mode]

    colors = {
        key: hex_to_rgba(value)
        for key, value in mode_colors.items()
    }

    colors.update(
        {
            "primary": hex_to_rgba(
                palette["primary"]
            ),
            "primary_hover": hex_to_rgba(
                palette["primary_hover"]
            ),
            "primary_soft": hex_to_rgba(
                palette["primary_soft"]
            ),
            "white": hex_to_rgba("#FFFFFF"),
            "blue": hex_to_rgba("#3B82F6"),
            "green": hex_to_rgba("#22C55E"),
            "orange": hex_to_rgba("#F59E0B"),
            "red": hex_to_rgba("#EF4444"),
            "pink": hex_to_rgba("#EC4899"),
        }
    )

    return colors