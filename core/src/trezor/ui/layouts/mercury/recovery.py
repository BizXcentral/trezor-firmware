from typing import Callable, Iterable

import trezorui2
from trezor import TR
from trezor.enums import ButtonRequestType, RecoveryType

from ..common import interact
from . import RustLayout, raise_if_not_confirmed

CONFIRMED = trezorui2.CONFIRMED  # global_import_cache
CANCELLED = trezorui2.CANCELLED  # global_import_cache
INFO = trezorui2.INFO  # global_import_cache


async def request_word_count(recovery_type: RecoveryType) -> int:
    selector = RustLayout(trezorui2.select_word_count(recovery_type=recovery_type))
    count = await interact(selector, "word_count", ButtonRequestType.MnemonicWordCount)
    return int(count)


async def request_word(
    word_index: int, word_count: int, is_slip39: bool, prefill_word: str = ""
) -> str:
    prompt = TR.recovery__word_x_of_y_template.format(word_index + 1, word_count)
    can_go_back = word_index > 0
    if is_slip39:
        keyboard = RustLayout(
            trezorui2.request_slip39(
                prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
            )
        )
    else:
        keyboard = RustLayout(
            trezorui2.request_bip39(
                prompt=prompt, prefill_word=prefill_word, can_go_back=can_go_back
            )
        )

    word: str = await keyboard
    return word


async def show_remaining_shares(
    groups: Iterable[tuple[int, tuple[str, ...]]],  # remaining + list 3 words
    shares_remaining: list[int],
    group_threshold: int,
) -> None:
    from trezor import strings
    from trezor.crypto.slip39 import MAX_SHARE_COUNT

    pages: list[tuple[str, str]] = []
    for remaining, group in groups:
        if 0 < remaining < MAX_SHARE_COUNT:
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                remaining,
                TR.plurals__x_shares_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))
        elif (
            remaining == MAX_SHARE_COUNT and shares_remaining.count(0) < group_threshold
        ):
            groups_remaining = group_threshold - shares_remaining.count(0)
            title = strings.format_plural(
                TR.recovery__x_more_items_starting_template_plural,
                groups_remaining,
                TR.plurals__x_groups_needed,
            )
            words = "\n".join(group)
            pages.append((title, words))

    await raise_if_not_confirmed(
        interact(
            RustLayout(trezorui2.show_remaining_shares(pages=pages)),
            "show_shares",
            ButtonRequestType.Other,
        )
    )


async def show_group_share_success(share_index: int, group_index: int) -> None:
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_group_share_success(
                    lines=[
                        TR.recovery__you_have_entered,
                        TR.recovery__share_num_template.format(share_index + 1),
                        TR.words__from,
                        TR.recovery__group_num_template.format(group_index + 1),
                    ],
                )
            ),
            "share_success",
            ButtonRequestType.Other,
        )
    )


async def continue_recovery(
    button_label: str,  # unused on mercury
    text: str,
    subtext: str | None,
    info_func: Callable | None,  # TODO: see below
    recovery_type: RecoveryType,
    show_info: bool = False,
) -> bool:
    # TODO: info_func should be changed to return data to be shown (and not show
    # them) so that individual models can implement showing logic on their own.
    # T3T1 should move the data to `flow_continue_recovery` and hide them
    # in the context menu

    # NOTE: show_info can be understood as first screen before any shares
    # NOTE: button request sent from the flow
    homepage = RustLayout(
        trezorui2.flow_continue_recovery(
            first_screen=show_info,
            recovery_type=recovery_type,
            text=text,
            subtext=subtext,
        )
    )
    result = await homepage
    return result is CONFIRMED


async def show_recovery_warning(
    br_name: str,
    content: str,
    subheader: str | None = None,
    button: str | None = None,
    br_code: ButtonRequestType = ButtonRequestType.Warning,
) -> None:
    button = button or TR.buttons__try_again  # def_arg
    await raise_if_not_confirmed(
        interact(
            RustLayout(
                trezorui2.show_warning(
                    title=content or TR.words__warning,
                    value=subheader or "",
                    button=button,
                    description="",
                )
            ),
            br_name,
            br_code,
        )
    )
