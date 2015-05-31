import os
import sys
import math
from contextlib import contextmanager

usage = '''Usage: {} INPUTBIN OUTFILE
produces PROM implementation from given binary data
'''

@contextmanager
def new_subckt(name, arity):
  # we start numbering of input nodes from 1, since zero is GND
  print(".SUBCKT {} {} out VDD".format(name, ' '.join(map(str, range(1, arity + 1)))))
  yield
  end_subckt(name)

def end_subckt(name):
  print(".ENDS {}\n".format(name))

def gen_t_and(name, arity):
  with new_subckt(name, arity):
    print "* THIS WILL BE n-AND"

def gen_inv():
  with new_subckt('INV', 2):
    print "* THIS WILL BE CMOS INVERTOR"

def gen_buf():
  with new_subckt('BUF', 2):
    print "* THIS WILL BE CMOS BUFFER"

def gen_and_matcher(d, ident, and_name, bitlen, inps, outps):
  # input data, identifier, and model name, its input len in bits
  bits = bin(d)[2:].zfill(bitlen)
  print '* {}/{} - AND matcher for {}'.format(ident, bitlen, bits)
  bits = list(bits)
  bits.reverse()
  if ident[-3]=='3': print>>sys.stderr, ident, '\r ',
  for idx, (bit, inp) in enumerate(zip(bits, inps)):
    if bit == '0':
      #print 'XINV {}in{} {}inand{} VDD INV'.format(ident, idx, ident, idx)
      print 'XINV {} {}inand{} VDD INV'.format(inp, ident, idx)
    elif bit == '1':
      #print 'XBUF {}in{} {}inand{} VDD BUF'.format(ident, idx, ident, idx)
      print 'XBUF {} {}inand{} VDD BUF'.format(inp, ident, idx)
  print 'XAND {} {} VDD AND{}'.format(
      ' '.join(map(lambda _x: ident+'inand'+str(_x), range(bitlen))),
      outps[0], bitlen)

  print '\n'

def gen_ands(data):
  ln = len(data)
  # amount of inputs for AND gates
  bitlen = int(math.ceil(math.log(ln, 2)))

  # 'type' of and gate with arity, in string
  t_and = "AND{}".format(bitlen)
  gen_t_and(t_and, bitlen)
  gen_inv()
  gen_buf()

  print>>sys.stderr, 'tot ands: ', ln

  map(lambda _x: gen_and_matcher(_x, 'AND{}'.format(_x), t_and, bitlen, range(1,bitlen+1), ['AND'+str(_x)+'out']), xrange(ln))

def gen_ors(data, bitlen):
  idx = 0
  dl = len(data)
  for _i, d in enumerate(data):
    bits = bin(d)[2:].zfill(bitlen)
    bits = list(bits)
    bits.reverse()
    if _i & 0b00110 == 0b00110: print>>sys.stderr, _i, 'of', dl, '\r ',
    for bidx, bit in enumerate(bits):
      if bit == '1':
        print 'Dor{} AND{}out BUF{}in 1N4148'.format(idx, idx, bidx)
        idx = idx + 1

  for x in range(bitlen):
    print 'XoBUF{} BUF{}in PROMout{} VDD BUF'.format(x, x, x)
  print '\n'

def main():
  if len(sys.argv) < 3:
    print(usage.format(sys.argv[0]))
    exit(1)

  finame = sys.argv[1]
  foname = sys.argv[2]
  with open(finame) as fin:
    d = fin.read()
    gen_ands(d)
    gen_ors(map(ord, d), 8) # data "byte" is 8 bits
    with open(foname, 'w') as fout:
      fout.write(d)

if __name__=='__main__':
  main()
