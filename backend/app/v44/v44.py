# -*- coding: utf-8 -*-
"""
V.44 Data Compression - Pure Python Implementation
ITU-T V.44:2000 with Packet Method (Annex B.1)

For use in DLMS/COSEM protocol (Security Suite 1 and 2)
Ported from C reference implementation.
"""

from typing import List, Tuple, Optional

# ============================================================================
# Configuration Parameters
# ============================================================================

# Maximum number of codewords (including 4 control codes)
# Packet Method default: 1525
V44_N2 = 1525

# Alphabet size (8-bit characters)
V44_N4 = 256

# Number of control codes / first available codeword
V44_N5 = 4

# Maximum string length (Packet Method default: 255)
V44_N7 = 255

# Initial ordinal size (bits)
V44_C5_INIT_BIT7 = 7
V44_C5_INIT_BIT8 = 8

# Initial codeword size (bits). DLMS always uses 6.
V44_C2_INIT = 6

# Initial codeword threshold. Corresponds to 2^C2_INIT.
V44_C3_INIT = 64

# Maximum codeword size (bits)
V44_N1_MAX = 120

# Invalid index sentinel value
V44_INVALID_INDEX = 0xFFFF

# Bit buffer size for encoding output
V44_BITBUF_SIZE = 4096

# ============================================================================
# Control Code values
# ============================================================================

V44_CTRL_ETM = 0        # Enter Transparent Mode
V44_CTRL_FLUSH = 1      # Flush data
V44_CTRL_STEPUP = 2     # Increase codeword or ordinal size by 1
V44_CTRL_REINIT = 3     # Force reinitialization of dictionaries

# ============================================================================
# Error codes
# ============================================================================

V44_OK = 0
V44_ERR_BUFFER_FULL = -1
V44_ERR_INVALID_CODE = -2
V44_ERR_OUTPUT_FULL = -3
V44_ERR_INPUT_EMPTY = -4


# ============================================================================
# Bitstream Writer (for encoder)
# ============================================================================

class V44BitstreamWriter:
    """Bit-level output context for V.44 encoder (LSB-first packing)."""

    def __init__(self):
        self.buf = bytearray()
        self.bit_acc = 0       # Bit accumulator
        self.bit_count = 0     # Bits in accumulator

    def put_bit(self, bit: int) -> None:
        """Write a single bit (LSB-first: first bit goes to bit 0)."""
        self.bit_acc |= (bit & 1) << self.bit_count
        self.bit_count += 1
        if self.bit_count == 8:
            self.buf.append(self.bit_acc & 0xFF)
            self.bit_acc = 0
            self.bit_count = 0

    def write_bits(self, value: int, num_bits: int) -> None:
        """Write multiple bits LSB-first: bit 0 of value goes to bitstream first."""
        for i in range(num_bits):
            self.put_bit((value >> i) & 1)

    def flush(self) -> None:
        """Flush remaining bits with zeros for byte alignment."""
        if self.bit_count > 0:
            self.buf.append(self.bit_acc & 0xFF)
            self.bit_acc = 0
            self.bit_count = 0

    def get_bytes(self) -> bytes:
        """Get the compressed byte data."""
        return bytes(self.buf)


# ============================================================================
# Bitstream Reader (for decoder)
# ============================================================================

class V44BitstreamReader:
    """Bit-level input context for V.44 decoder (LSB-first packing)."""

    def __init__(self, data: bytes):
        self.data = data
        self.data_len = len(data)
        self.data_pos = 0
        self.bit_acc = 0       # Bit accumulator
        self.bit_count = 0     # Bits remaining in accumulator

    def read_bit(self) -> int:
        """Read a single bit. Returns 0 or 1, or -1 on end of data."""
        if self.bit_count == 0:
            if self.data_pos >= self.data_len:
                return -1
            self.bit_acc = self.data[self.data_pos]
            self.data_pos += 1
            self.bit_count = 8

        # LSB-first packing: read from bit 0, then bit 1, etc.
        pos = 8 - self.bit_count
        bit = (self.bit_acc >> pos) & 1
        self.bit_count -= 1
        return bit

    def read_bits(self, num_bits: int) -> Tuple[int, int]:
        """Read multiple bits LSB-first. Returns (value, status).
        status: 0=OK, -1=error"""
        val = 0
        for i in range(num_bits):
            bit = self.read_bit()
            if bit < 0:
                return 0, -1
            val |= bit << i
        return val, 0


# ============================================================================
# Extension Length Encoding/Decoding (Tables 3 and 4 / V.44)
# ============================================================================

def v44_encode_ext_length(length: int) -> Tuple[int, int]:
    """Encode a string-extension length.
    Returns (num_bits, pattern) or (-1, -1) on error."""
    if length < 1 or length > 253:
        return -1, -1

    if length == 1:
        return 1, 0x1
    elif length == 2:
        return 3, 0x2
    elif length == 3:
        return 3, 0x4
    elif length == 4:
        return 3, 0x6

    if length <= 12:
        # 7 bits: 4 zero prefix bits + 3 LSB-first value bits
        return 7, (length - 5) << 4

    # Lengths 13-253 (Table 4/V.44)
    # 4 prefix bits (0001) + num_val_bits LSB-first value bits
    if V44_N7 <= 46:
        num_val_bits = 5
    elif V44_N7 <= 78:
        num_val_bits = 6
    elif V44_N7 <= 142:
        num_val_bits = 7
    else:
        num_val_bits = 8

    val = length - 13
    num_bits = 4 + num_val_bits
    # Subfields are transmitted as 0,00,1,N0..Nk in LSB-first order.
    # Marker bit occupies bit 3, value starts at bit 4.
    pattern = 0x8 | (val << 4)
    return num_bits, pattern


def v44_decode_ext_length(reader: V44BitstreamReader) -> int:
    """Decode a string-extension length from a bitstream.
    Returns extension length (>= 1), or -1 on error."""
    bit0 = reader.read_bit()
    if bit0 < 0:
        return -1
    if bit0 == 1:
        return 1

    bit1 = reader.read_bit()
    if bit1 < 0:
        return -1

    if bit1 == 1:
        bit2 = reader.read_bit()
        if bit2 < 0:
            return -1
        return 4 if bit2 else 2

    bit2 = reader.read_bit()
    if bit2 < 0:
        return -1
    if bit2 == 1:
        return 3

    bit3 = reader.read_bit()
    if bit3 < 0:
        return -1
    if bit3 == 0:
        lsb_val = 0
        for i in range(3):
            bit = reader.read_bit()
            if bit < 0:
                return -1
            lsb_val |= (bit & 1) << i
        return 5 + lsb_val

    if V44_N7 <= 46:
        num_val_bits = 5
    elif V44_N7 <= 78:
        num_val_bits = 6
    elif V44_N7 <= 142:
        num_val_bits = 7
    else:
        num_val_bits = 8

    val = 0
    for i in range(num_val_bits):
        bit = reader.read_bit()
        if bit < 0:
            return -1
        val |= (bit & 1) << i
    return 13 + val


# ============================================================================
# Encoder Node
# ============================================================================

class V44EncoderNode:
    """Encoder node entry (for node tree)."""

    def __init__(self):
        self.history_index = 0      # Position of first character in history
        self.segment_length = 0     # Length of this string segment
        self.down_index = V44_INVALID_INDEX   # Index to child node
        self.side_index = V44_INVALID_INDEX   # Index to sibling node


# ============================================================================
# V.44 Encoder
# ============================================================================

class V44Encoder:
    """V.44 Packet Method Encoder."""

    def __init__(self, c5_init: int = V44_C5_INIT_BIT7):
        """Initialize encoder to initial state.
        Args:
            c5_init: Initial ordinal size in bits (typically 7 or 8).
        """
        self.node_tree = [V44EncoderNode() for _ in range(V44_N2)]
        self.root = [V44_INVALID_INDEX] * V44_N4
        self.C1 = V44_N5        # First available codeword = 4
        self.C2 = V44_C2_INIT   # 6 bits
        self.C3 = V44_C3_INIT   # 64
        self.C4 = 0             # History position
        self.C5 = c5_init       # Current ordinal size (bits)
        self.input_data = None
        self.input_len = 0

    def _get_input_char(self, pos: int) -> int:
        """Get input character at position."""
        if pos < self.input_len:
            return self.input_data[pos]
        return 0

    def _write_ordinal(self, ch: int, after_codeword: bool, bs: V44BitstreamWriter) -> None:
        """Write ordinal with prefix and STEPUP."""
        prefix_after_codeword = after_codeword

        # Check if STEPUP needed
        if self.C5 == 7 and ch >= 128:
            bs.write_bits(0x01, 1)              # prefix "1"
            bs.write_bits(V44_CTRL_STEPUP, self.C2)
            self.C5 = 8
            prefix_after_codeword = False

        # Code prefix
        if prefix_after_codeword:
            bs.write_bits(0x00, 2)   # "00" after codeword
        else:
            bs.write_bits(0x00, 1)   # "0"

        # Ordinal value
        bs.write_bits(ch, self.C5)

    def _write_codeword(self, codeword: int, bs: V44BitstreamWriter) -> None:
        """Write codeword with prefix and STEPUP."""
        # STEPUP loop: grow codeword size until the codeword fits
        while codeword >= self.C3 and self.C2 < V44_N1_MAX:
            bs.write_bits(0x01, 1)              # prefix "1"
            bs.write_bits(V44_CTRL_STEPUP, self.C2)
            self.C2 += 1
            self.C3 <<= 1

        # Code prefix "1"
        bs.write_bits(0x01, 1)
        # Codeword value
        bs.write_bits(codeword, self.C2)

    def _write_ext_length(self, length: int, bs: V44BitstreamWriter) -> None:
        """Write string-extension length with prefix "01"."""
        # prefix "01" (LSB-first: bit0=0, bit1=1)
        bs.write_bits(0x02, 2)

        num_bits, pattern = v44_encode_ext_length(length)
        if num_bits >= 0:
            bs.write_bits(pattern, num_bits)

    def _write_control(self, code: int, bs: V44BitstreamWriter) -> None:
        """Write control code with prefix "1"."""
        bs.write_bits(0x01, 1)   # prefix "1"
        bs.write_bits(code, self.C2)

    def _create_node(self, hist_idx: int, seg_len: int) -> int:
        """Create new node. Returns codeword or V44_INVALID_INDEX if full."""
        if self.C1 >= V44_N2:
            return V44_INVALID_INDEX

        cw = self.C1
        self.node_tree[cw].history_index = hist_idx
        self.node_tree[cw].segment_length = seg_len
        self.node_tree[cw].down_index = V44_INVALID_INDEX
        self.node_tree[cw].side_index = V44_INVALID_INDEX
        self.C1 += 1
        return cw

    def _link_as_child(self, parent_cw: int, child_cw: int) -> None:
        """Link a new node as child of a parent node (via down_index)."""
        if self.node_tree[parent_cw].down_index == V44_INVALID_INDEX:
            self.node_tree[parent_cw].down_index = child_cw
        else:
            last = self.node_tree[parent_cw].down_index
            while self.node_tree[last].side_index != V44_INVALID_INDEX:
                last = self.node_tree[last].side_index
            self.node_tree[last].side_index = child_cw

    def _link_as_root_child(self, ch: int, child_cw: int) -> None:
        """Link a new node as root child."""
        if self.root[ch] == V44_INVALID_INDEX:
            self.root[ch] = child_cw
        else:
            last = self.root[ch]
            while self.node_tree[last].side_index != V44_INVALID_INDEX:
                last = self.node_tree[last].side_index
            self.node_tree[last].side_index = child_cw

    def _string_match(self, pos: int) -> Tuple[int, int, int]:
        """String matching (Section 6.3.1).
        Returns (matched_codeword, ext_input_pos, ext_hist_pos).
        matched_codeword: >= V44_N5 if match found, 0 if no match.
        """
        first = self._get_input_char(pos)
        root_idx = self.root[first]
        base_pos = pos

        if root_idx == V44_INVALID_INDEX:
            return 0, pos + 1, 0

        best_cw = 0
        node_idx = root_idx
        matched_total = 1

        while node_idx != V44_INVALID_INDEX:
            node = self.node_tree[node_idx]
            seg_hist = node.history_index
            seg_len = node.segment_length

            # Compare segment with input
            full_match = True
            for i in range(seg_len):
                inp = base_pos + matched_total + i
                if inp >= self.input_len:
                    full_match = False
                    break
                if (self._get_input_char(inp) !=
                        self._get_input_char(seg_hist + i)):
                    full_match = False
                    break

            if full_match:
                best_cw = node_idx
                matched_total += seg_len
                node_idx = node.down_index
            else:
                # Try sibling
                node_idx = node.side_index

        ext_input_pos = base_pos + matched_total
        ext_hist_pos = 0
        if best_cw != 0:
            last = self.node_tree[best_cw]
            ext_hist_pos = last.history_index + last.segment_length

        return best_cw, ext_input_pos, ext_hist_pos

    def _string_extend(self, input_pos: int, hist_pos: int,
                       matched_len: int) -> int:
        """String extension (Section 6.3.2).
        Returns number of extension characters."""
        count = 0

        if matched_len >= V44_N7:
            return 0
        max_ext = V44_N7 - matched_len
        if max_ext > 253:
            max_ext = 253
        if max_ext == 0:
            return 0
        if hist_pos >= self.C4:
            return 0

        # V.44 string-extension permits overlap with characters being extended
        while count < max_ext and input_pos + count < self.input_len:
            if (self._get_input_char(input_pos + count) ==
                    self._get_input_char(hist_pos + count)):
                count += 1
            else:
                break
        return count

    def _encode_flush(self, bs: V44BitstreamWriter) -> None:
        """Send FLUSH control code + byte alignment padding."""
        self._write_control(V44_CTRL_FLUSH, bs)
        bs.flush()

    def encode(self, input_data: bytes) -> bytes:
        """Compress input data using V.44 Packet Method.

        Args:
            input_data: Input data bytes to compress

        Returns:
            Compressed data bytes

        Raises:
            ValueError: on buffer overflow
        """
        if not input_data:
            bs = V44BitstreamWriter()
            self._encode_flush(bs)
            return bs.get_bytes()

        self.input_data = input_data
        self.input_len = len(input_data)

        bs = V44BitstreamWriter()
        pos = 0
        after_cw = False

        while pos < self.input_len:
            cw, ext_input_pos, ext_hist_pos = self._string_match(pos)

            if cw == 0:
                # No match - output ordinal
                ch = self._get_input_char(pos)
                if self.C1 < V44_N2:
                    n = self._create_node(pos + 1, 1)
                    if n != V44_INVALID_INDEX:
                        self._link_as_root_child(ch, n)
                self._write_ordinal(ch, after_cw, bs)
                after_cw = False
                self.C4 += 1
                pos += 1
            else:
                # Match found - output codeword
                self._write_codeword(cw, bs)
                after_cw = True

                # Calculate how many characters were matched
                matched = ext_input_pos - pos
                pos = ext_input_pos

                # Update C4 BEFORE string_extend
                self.C4 += matched

                # Try string extension
                if pos < self.input_len:
                    ext_len = self._string_extend(pos, ext_hist_pos, matched)
                    if ext_len > 0:
                        self._write_ext_length(ext_len, bs)
                        after_cw = False

                        if self.C1 < V44_N2:
                            n = self._create_node(pos, ext_len)
                            if n != V44_INVALID_INDEX:
                                self._link_as_child(cw, n)

                        self.C4 += ext_len
                        pos += ext_len
                    else:
                        # Extension failed: add one-character child
                        if pos < self.input_len:
                            if self.C1 < V44_N2:
                                n = self._create_node(pos, 1)
                                if n != V44_INVALID_INDEX:
                                    self._link_as_child(cw, n)
                        continue

        self._encode_flush(bs)
        return bs.get_bytes()


# ============================================================================
# Decoder String Entry
# ============================================================================

class V44DecoderString:
    """Decoder string entry."""

    def __init__(self):
        self.last_char_pos = 0    # Position of last character in history
        self.string_length = 0    # Total string length


# ============================================================================
# V.44 Decoder
# ============================================================================

class V44Decoder:
    """V.44 Packet Method Decoder (Decompressor)."""

    def __init__(self, c5_init: int = V44_C5_INIT_BIT7):
        """Initialize decoder to initial state.
        Args:
            c5_init: Initial ordinal size in bits (typically 7 or 8).
        """
        self.strings = [V44DecoderString() for _ in range(V44_N2)]
        self.C1 = V44_N5        # Next available codeword
        self.C2 = V44_C2_INIT   # Current codeword size (bits)
        self.C4 = 0             # Current history position
        self.C5 = c5_init       # Current ordinal size (bits)
        self.output_data = None
        self.output_capacity = 0
        self.output_len = 0

    def reset(self) -> None:
        """Reset decoder dictionary (Packet Method: between PDU processing)."""
        self.C1 = V44_N5
        self.C2 = V44_C2_INIT
        self.C4 = 0

    def _get_string_first_char(self, cw: int) -> int:
        """Get first character of a decoded string."""
        if cw >= self.C1:
            return 0
        s = self.strings[cw]
        if s.string_length == 0 or s.last_char_pos + 1 < s.string_length:
            return 0
        start = s.last_char_pos + 1 - s.string_length
        return self.output_data[start]

    def _output_char(self, ch: int) -> bool:
        """Output a single character. Returns False if buffer full."""
        if self.output_len >= self.output_capacity:
            return False
        self.output_data[self.output_len] = ch
        self.output_len += 1
        return True

    def _create_string(self, cw: int, last_pos: int, length: int) -> None:
        """Create string entry."""
        if cw < V44_N2:
            self.strings[cw].last_char_pos = last_pos
            self.strings[cw].string_length = length

    def decode(self, compressed: bytes) -> bytes:
        """Decompress V.44 Packet Method compressed data.

        Args:
            compressed: Compressed data bytes

        Returns:
            Decompressed data bytes

        Raises:
            ValueError: on invalid code or buffer overflow
        """
        if not compressed:
            return b''

        reader = V44BitstreamReader(compressed)

        # Estimate output capacity (start with 4x compressed size)
        out_cap = max(len(compressed) * 4, 4096)
        self.output_data = bytearray(out_cap)
        self.output_capacity = out_cap
        self.output_len = 0

        # Previous-item tracking for string creation
        prev_codeword = 0
        prev_type = 0       # 0=none, 1=ordinal, 2=codeword, 3=extension
        prev_str_start = 0
        prev_str_end = 0
        prev_ordinal = 0
        prefix_after_codeword = False
        pending_stepup = False

        while True:
            # Read code prefix bit
            bit = reader.read_bit()
            if bit < 0:
                break  # End of input data

            if bit == 1:
                if pending_stepup:
                    if self.C2 >= V44_N1_MAX:
                        raise ValueError("V44_ERR_INVALID_CODE: codeword size exceeded")
                    self.C2 += 1
                    pending_stepup = False

                # ---- Bit prefix "1": control code or codeword ----
                code_val, status = reader.read_bits(self.C2)
                if status < 0:
                    break

                if code_val < V44_N5:
                    # ---- Control code ----
                    if code_val == V44_CTRL_FLUSH:
                        # Packet Method test streams end at FLUSH
                        return bytes(self.output_data[:self.output_len])

                    elif code_val == V44_CTRL_STEPUP:
                        # STEPUP applies to the next transferred code
                        pending_stepup = True
                        prefix_after_codeword = False

                    elif code_val == V44_CTRL_REINIT:
                        # REINIT: reset decoder to initial state
                        self.reset()
                        prev_type = 0
                        prev_codeword = 0
                        prev_str_start = 0
                        prev_str_end = 0
                        prev_ordinal = 0
                        prefix_after_codeword = False
                        pending_stepup = False

                    elif code_val == V44_CTRL_ETM:
                        # ETM: not used in Packet Method, treat as no-op
                        prefix_after_codeword = False

                    # STEPUP/ETM do not break the previous-item chain
                    if (code_val != V44_CTRL_STEPUP and
                        code_val != V44_CTRL_ETM and
                        code_val != V44_CTRL_REINIT):
                        prev_type = 0

                elif code_val == self.C1 and self.C1 < V44_N2:
                    # ---- Future codeword (Section 6.4.1 steps 3-4) ----
                    if prev_type in (2, 3):
                        # Step 3: Previous was a codeword
                        s = self.strings[prev_codeword]
                        str_len = s.string_length
                        str_end = s.last_char_pos

                        if str_len > 0 and str_end + 1 >= str_len:
                            src_start = str_end + 1 - str_len
                            for i in range(src_start, str_end + 1):
                                if self.output_len >= self.output_capacity:
                                    self._grow_output()
                                self.output_data[self.output_len] = self.output_data[i]
                                self.output_len += 1

                        # Append first character of the previous string
                        first = self._get_string_first_char(prev_codeword)
                        if self.output_len >= self.output_capacity:
                            self._grow_output()
                        self.output_data[self.output_len] = first
                        self.output_len += 1

                        # Create new string at C1
                        new_len = str_len + 1
                        if new_len > V44_N7:
                            raise ValueError("V44_ERR_INVALID_CODE: string too long")
                        self._create_string(self.C1, self.output_len - 1, new_len)

                    else:
                        # Step 4: Previous was ordinal
                        if self.output_len < 1:
                            raise ValueError("V44_ERR_INVALID_CODE: no previous ordinal")
                        ch = prev_ordinal & 0xFF
                        if self.output_len + 2 > self.output_capacity:
                            self._grow_output()
                        self.output_data[self.output_len] = ch
                        self.output_len += 1
                        self.output_data[self.output_len] = ch
                        self.output_len += 1

                        # Created codeword ends at first appended char
                        self._create_string(self.C1, self.output_len - 2, 2)

                    prev_codeword = self.C1
                    self.C1 += 1
                    prev_type = 2
                    s = self.strings[prev_codeword]
                    prev_str_start = s.last_char_pos + 1 - s.string_length
                    prev_str_end = s.last_char_pos + 1
                    prefix_after_codeword = True

                elif code_val < self.C1:
                    # ---- Normal codeword (Section 6.4.1 step 2) ----
                    s = self.strings[code_val]
                    str_len = s.string_length
                    str_end = s.last_char_pos
                    copy_start = self.output_len

                    if str_len > 0 and str_end + 1 >= str_len:
                        src_start = str_end + 1 - str_len
                        for i in range(src_start, str_end + 1):
                            if self.output_len >= self.output_capacity:
                                self._grow_output()
                            self.output_data[self.output_len] = self.output_data[i]
                            self.output_len += 1

                    # Add new codeword defined by previous item and first char
                    if self.C1 < V44_N2 and prev_type == 1:
                        self._create_string(self.C1, copy_start, 2)
                        self.C1 += 1
                    elif self.C1 < V44_N2 and prev_type == 2:
                        prev_len = self.strings[prev_codeword].string_length
                        new_len = prev_len + 1
                        if new_len > V44_N7:
                            raise ValueError("V44_ERR_INVALID_CODE: string too long")
                        self._create_string(self.C1, copy_start, new_len)
                        self.C1 += 1

                    prev_codeword = code_val
                    prev_type = 2
                    prev_str_start = str_end + 1 - str_len
                    prev_str_end = str_end + 1
                    prefix_after_codeword = True

                else:
                    # Codeword > C1: invalid
                    raise ValueError("V44_ERR_INVALID_CODE: codeword out of range")

            else:
                if pending_stepup:
                    if self.C5 < 8:
                        self.C5 += 1
                    pending_stepup = False

                # ---- Bit prefix "0": ordinal or string extension ----
                bit2 = reader.read_bit()
                if bit2 < 0:
                    break

                if bit2 == 1 and prefix_after_codeword:
                    # ---- String-extension (prefix "01" after codeword) ----
                    ext_len = v44_decode_ext_length(reader)
                    if ext_len < 1:
                        raise ValueError("V44_ERR_INVALID_CODE: bad extension length")

                    hist_start = prev_str_end
                    for i in range(ext_len):
                        if hist_start + i >= self.output_len:
                            raise ValueError("V44_ERR_INVALID_CODE: extension out of range")
                        if self.output_len >= self.output_capacity:
                            self._grow_output()
                        self.output_data[self.output_len] = self.output_data[hist_start + i]
                        self.output_len += 1

                    # Create new string: prev_string + extension
                    new_len = (prev_str_end - prev_str_start) + ext_len
                    if new_len > V44_N7:
                        raise ValueError("V44_ERR_INVALID_CODE: string too long")
                    if self.C1 < V44_N2:
                        self._create_string(self.C1, self.output_len - 1, new_len)
                        prev_codeword = self.C1
                        self.C1 += 1

                    prev_type = 3
                    prev_str_start = self.output_len - new_len
                    prev_str_end = self.output_len
                    prefix_after_codeword = False

                else:
                    # ---- Ordinal ----
                    prior_type = prev_type

                    if prefix_after_codeword:
                        # After codeword: prefix "00" consumed, read C5 bits
                        ordinal_val = 0
                        for i in range(self.C5):
                            b = reader.read_bit()
                            if b < 0:
                                raise ValueError("V44_ERR_INPUT_EMPTY")
                            ordinal_val |= b << i
                    else:
                        # After ordinal/other: prefix "0" consumed, bit2 is first data bit
                        ordinal_val = bit2
                        for i in range(1, self.C5):
                            b = reader.read_bit()
                            if b < 0:
                                raise ValueError("V44_ERR_INPUT_EMPTY")
                            ordinal_val |= b << i

                    # Output the character
                    ch = ordinal_val & 0xFF
                    if not self._output_char(ch):
                        self._grow_output()
                        self._output_char(ch)
                    prev_ordinal = ordinal_val

                    # Create string per Table 2 (Section 6.4.2)
                    if prior_type == 2:
                        # After codeword: previous_string + ch
                        prev_len = self.strings[prev_codeword].string_length
                        new_len = prev_len + 1
                        if new_len > V44_N7:
                            raise ValueError("V44_ERR_INVALID_CODE: string too long")
                        if self.C1 < V44_N2:
                            self._create_string(self.C1, self.output_len - 1, new_len)
                            prev_codeword = self.C1
                            self.C1 += 1
                        prev_type = 1
                    elif prior_type == 1 and self.output_len >= 2:
                        # After ordinal: {prev_char, ch}
                        if self.C1 < V44_N2:
                            self._create_string(self.C1, self.output_len - 1, 2)
                            self.C1 += 1
                        prev_type = 1
                    else:
                        prev_type = 1

                    prev_str_start = self.output_len - 1
                    prev_str_end = self.output_len
                    prefix_after_codeword = False

        return bytes(self.output_data[:self.output_len])

    def _grow_output(self) -> None:
        """Grow the output buffer dynamically."""
        new_cap = self.output_capacity * 2
        new_buf = bytearray(new_cap)
        new_buf[:self.output_len] = self.output_data[:self.output_len]
        self.output_data = new_buf
        self.output_capacity = new_cap


# ============================================================================
# Convenience Functions
# ============================================================================

def v44_compress(data: bytes, ordinal_size: int = 7) -> bytes:
    """Compress data using V.44 Packet Method.

    Args:
        data: Input data bytes
        ordinal_size: Initial ordinal size in bits (7 or 8, default 7 for DLMS)

    Returns:
        Compressed data bytes
    """
    enc = V44Encoder(c5_init=ordinal_size)
    return enc.encode(data)


def v44_decompress(compressed: bytes, ordinal_size: int = 7) -> bytes:
    """Decompress V.44 Packet Method data.

    Args:
        compressed: Compressed data bytes
        ordinal_size: Initial ordinal size in bits (7 or 8, default 7 for DLMS)

    Returns:
        Decompressed data bytes
    """
    dec = V44Decoder(c5_init=ordinal_size)
    return dec.decode(compressed)


def v44_roundtrip(data: bytes, ordinal_size: int = 7) -> Tuple[bool, bytes, bytes]:
    """Test compress+decompress roundtrip.

    Args:
        data: Input data bytes
        ordinal_size: Initial ordinal size in bits

    Returns:
        Tuple of (success, compressed_data, decompressed_data)
    """
    compressed = v44_compress(data, ordinal_size)
    decompressed = v44_decompress(compressed, ordinal_size)
    success = (data == decompressed)
    return success, compressed, decompressed
