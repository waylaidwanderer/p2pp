__author__ = 'Tom Van den Eede'
__copyright__ = 'Copyright 2018-2020, Palette2 Splicer Post Processing Project'
__credits__ = ['Tom Van den Eede',
               'Tim Brookman'
               ]
__license__ = 'GPLv3'
__maintainer__ = 'Tom Van den Eede'
__email__ = 'P2PP@pandora.be'

from copy import deepcopy

import p2pp.gcode as gcode
import p2pp.variables as v


# routined to support more than 4 colors.
#########################################


# calculate the next n colors used in the print
###############################################

def calc_next(n, tools):
    nextn = []
    for idx in range(len(tools)):
        if not tools[idx] in nextn:
            nextn.append(tools[idx])
        if len(nextn) == n:
            return nextn
    return nextn


# find the color in the current loaded inputs that is last used in the sequence
# this is the most likely candidate to be replaced.
###############################################################################

def find_last_used(l, u):
    # if the color is no longer used... this is the prime candidate
    for i in range(len(l)):
        if l[i] not in u:
            return i

    # if the color is used further in the print... we take the one that is
    # furthest away to give more ealy lead time for uninterrupted swaps
    for i in range(len(u)):
        if u[-i] in l:
            return l.index(u[-i])


def find_previous_tool_replaced(tool, index):
    while index > 0:
        if v.m4c_toolchanges[index] == tool:
            return index
        index -= 1
    return -1


def patchup_toolchanges():
    for idx in range(len(v.m4c_toolchange_source_positions)):
        try:
            old = v.parsed_gcode[v.m4c_toolchange_source_positions[idx]]
        except:
            old = v.parsed_gcode[v.m4c_toolchange_source_positions[-1]]

        _ip = calculate_input_index(idx, int(old.Command_value))
        v.parsed_gcode[v.m4c_toolchange_source_positions[idx]] = gcode.GCodeCommand(
            "T{} ; INPUT MAPPING MORE THAN 4 COLORS {} --> {}".format(_ip, _ip, int(old.Command_value)))


def calculate_loadscheme():
    # input :
    #   v.splice_used_tool is the list of color changes
    # output:
    #   v.m4c_loadedinputs = list of loaded inputs per slice
    #   v.m4c_late_warning = list of swaps when prints MUST me paused
    #   v.m4c_early_warning = list of swaps when EARLY warning needs to be given
    #

    nexttools = []

    for idx in range(len(v.m4c_toolchanges)):
        nexttools.append(calc_next(-1, v.m4c_toolchanges[idx:]))

    loadedinputs = deepcopy(nexttools[0][:4])

    for idx in range(len(v.m4c_toolchanges) - 2):

        newtool = v.m4c_toolchanges[idx + 2]

        v.m4c_early_warning.append([])

        # checkif there is a tool we can unload
        if not newtool in loadedinputs:
            input_to_replace = find_last_used(loadedinputs, nexttools[idx])
            tool_replaced = loadedinputs[input_to_replace]
            v.m4c_late_warning.append([input_to_replace, tool_replaced, newtool])
            # print("{} FROM Loaded {} - Next {} ".format(input_to_replace, loadedinputs, nexttools[idx]))
            # print ("Splice {} Changing Input {} from {} to {}".format(idx,input_to_replace, tool_replaced, newtool ))
            loadedinputs[input_to_replace] = newtool
            last_used = find_previous_tool_replaced(tool_replaced, idx)
            if last_used > 0 and not last_used == idx:
                v.m4c_early_warning[last_used + 1] = v.m4c_late_warning[-1]
        else:
            v.m4c_late_warning.append([])

        v.m4c_loadedinputs.append(deepcopy(loadedinputs))

    v.m4c_loadedinputs.append(deepcopy(loadedinputs))
    v.m4c_loadedinputs.append(deepcopy(loadedinputs))

    if v.m4c_numberoffilaments <= 4:
        for idx in v.m4c_loadedinputs[0]:
            v.palette_inputs_used[idx] = True
    else:
        for idx in range(len(v.m4c_loadedinputs[0])):
            v.palette_inputs_used[idx] = True

    patchup_toolchanges()


########################################################################
# the following function gets the input index of s apecific loaded color
# the returned value is 0-based
########################################################################
def calculate_input_index(swap, color):
    try:
        return v.m4c_loadedinputs[swap].index(color)
    except:
        return 0


M4C_LATE = 1
M4C_EARLY = 0


def generate_warninglist(type):
    template = "O50{} D{} D{} D{} D{} D{}"

    result = []

    for idx in range(len(v.m4c_early_warning)):

        if type == M4C_EARLY:
            tmp_value = v.m4c_early_warning[idx]
        else:
            tmp_value = v.m4c_late_warning[idx]

        if len(tmp_value) > 0:
            result.append(template.format(type,
                                          idx,
                                          int(v.splice_length[idx]),
                                          tmp_value[0],
                                          tmp_value[1],
                                          tmp_value[2]))
    return result