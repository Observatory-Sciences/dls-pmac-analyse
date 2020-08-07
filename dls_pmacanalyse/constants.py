class Constants:
    """contains the global constants for describing pmacs."""

    coord_sys_numbers = range(1, 17)
    macro_station_nodes = [0, 16, 32, 64]
    p_variable_numbers = range(8192)
    m_variable_numbers = range(8192)
    q_variable_numbers = range(100)
    i_variable_global_numbers = range(100)
    i_variable_motor_numbers = range(100)
    motor_numbers = range(1, 33)
    plc_numbers = range(32)
    prog_numbers = range(256)

    axisToNode = {
        1: 0,
        2: 1,
        3: 4,
        4: 5,
        5: 8,
        6: 9,
        7: 12,
        8: 13,
        9: 16,
        10: 17,
        11: 20,
        12: 21,
        13: 24,
        14: 25,
        15: 28,
        16: 29,
        17: 32,
        18: 33,
        19: 36,
        20: 37,
        21: 40,
        22: 41,
        23: 44,
        24: 45,
        25: 48,
        26: 49,
        27: 52,
        28: 53,
        29: 56,
        30: 57,
        31: 60,
        32: 61,
    }
    axisToMn = {
        1: 10,
        2: 20,
        3: 30,
        4: 40,
        5: 110,
        6: 120,
        7: 130,
        8: 140,
        9: 210,
        10: 220,
        11: 230,
        12: 240,
        13: 310,
        14: 320,
        15: 330,
        16: 340,
    }

    @classmethod
    def i_variable_motor7000_numbers(cls, motor: int):
        start = 7000 + cls.axisToMn[motor]
        return range(start, start + 10)
