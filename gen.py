import os
import sys
import math
from contextlib import contextmanager

usage = '''Usage: {} INPUTBIN OUTFILE
produces PROM implementation from given binary data
'''

trans = 0
@contextmanager
def new_subckt(name, arity, extra=None):
  # we start numbering of input nodes from 1, since zero is GND
  if extra is None:
    extra = []
  print(".SUBCKT {} {} VDD".format(name, ' '.join(map(str, range(1, arity + 1)) + extra)))

  yield
  end_subckt(name)

def end_subckt(name):
  #print(".ENDS {}\n".format(name))
  print(".ENDS")

def gen_t_and(name, arity):
  with new_subckt(name, arity, ["out"]):
    print "* THIS WILL BE n-AND"
    ox = 'VDD'
    for x in xrange(1, arity):
      #           d  g   s   b
      print "MP{} {} {} {} {} PMOS".format(x, ox, x, 's'+str(x), 's'+str(x))
      ox = "s{}".format(x)
    x = arity
    print "MP{} {} {} out out PMOS".format(x, ox, x)

    ox = 'out'
    for x in xrange(arity, 1, -1):
      print "MN{} {} {} {} {} NMOS".format(x, ox, x, 'z'+str(x), 'z'+str(x))
      ox = "z{}".format(x)
    x = 1
    print "MN{} {} {} 0 0 NMOS".format(x, ox, x)
    print ".model nmos pmos level=54 version=4.7"
    print ".model pmos nmos level=54 version=4.7"


def gen_inv():
  with new_subckt('INV', 2):
    print "* THIS WILL BE CMOS INVERTOR"
    print "MP vdd 1 2 2 PMOS"
    print "MN   2 1 0 0 NMOS"
    print ".model nmos nmos level=54 version=4.7"
    print ".model pmos pmos level=54 version=4.7"

def gen_buf():
  with new_subckt('BUF', 2):
    print "* THIS WILL BE CMOS BUFFER"
    print "XINV1 1 3 VDD INV"
    print "XINV2 3 2 VDD INV"

xinvid=1
def xinv(inp, outp):
  global trans
  global xinvid
  print('XINV{} {} {} VDD INV'.format(xinvid, inp, outp))
  xinvid = xinvid + 1
  trans += 2

xbufid=1
def xbuf(inp, outp):
  global xbufid
  global trans
  print('XBUF{} {} {} VDD BUF'.format(xbufid, inp, outp))
  xbufid = xbufid + 1
  trans += 4

xandid=1
def xand(input_arity, inps, outp):
  global xandid
  global trans
  print('XAND{} {} {} VDD AND{}'.format(xandid, ' '.join(inps), outp, input_arity))
  xandid = xandid + 1
  trans += 2*input_arity

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
      #print 'XINV{} {} {}inand{} VDD INV'.format(idx, inp, ident, idx)
      xinv(inp, "{}inand{}".format(ident, idx))
    elif bit == '1':
      #print 'XBUF {}in{} {}inand{} VDD BUF'.format(ident, idx, ident, idx)
      #print 'XBUF{} {} {}inand{} VDD BUF'.format(idx, inp, ident, idx)
      xbuf(inp, "{}inand{}".format(ident, idx))
#  print 'XAND {} {} VDD AND{}'.format(
#      ' '.join(map(lambda _x: ident+'inand'+str(_x), range(bitlen))),
#      outps[0], bitlen)
  xand(bitlen, map(lambda _x: ident+'inand'+str(_x), range(bitlen)), outps[0])

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
        print 'Dor{} AND{}out BUF{}in 1N4148'.format(idx, _i, bidx)
        idx = idx + 1

  for x in map(str, range(bitlen)):
    print 'Rbuf{} BUF{}in 0 250k'.format(x, x)
    xbuf('BUF'+x+'in', 'PROMout'+x)
    #print 'XoBUF{} BUF{}in PROMout{} VDD BUF'.format(x, x, x)
  print ".model 1N4148 D"
  print '\n'

def main():
  if len(sys.argv) < 3:
    print(usage.format(sys.argv[0]))
    exit(1)

  finame = sys.argv[1]
  foname = sys.argv[2]
  with open(finame) as fin:
    d = fin.read()
    print "CMOS n-bit PROM"
    gen_ands(d)
    gen_ors(map(ord, d), 8) # data "byte" is 8 bits

    bitlen = int(math.ceil(math.log(len(d), 2)))
    for x in xrange(1, bitlen + 1):
      print "R{} {} 0 100k".format(x, x)

    for x in xrange(1, 8+1): # 8 bits word + 1
      print "Rpo{} PROMout{} 0 100k".format(x, x)

    print 'V1 VDD 0 DC 5V'

    print 'L1 kokot ckot 10m'
    print 'C1 ckot kokot2 10m'
    print 'C2 ckot 0 22p'
    print 'Rkkt kokot VDD 250k'
    xinv('kokot2', 'k2')
    xinv('k3', 'k4')
    xinv('k5', 'k6')
    xinv('k6', 'k7')
    xinv('k7', 'k8')
    xinv('k8', 'k9')
    xinv('k9', 'kokot')

    print ".control"
    print "tran 1ms 1s"
    print "plot v(PROMout0), v(PROMout1), v(PROMout2), v(PROMout3), v(PROMout4), v(PROMout5), v(PROMout6), v(PROMout7)"
    for _xx in xrange(8):
      print "plot v(PROMout{})".format(_xx)
    #print "plot "+", ".join(['v(AND'+str(x)+'out)' for x in xrange(len(d))])
    print "write sim.out"
    print ".endc"
    print ".end"
    global trans
    print>>sys.stderr, "total: ", trans, 'transistors'
    with open(foname, 'w') as fout:
      fout.write(d)

if __name__=='__main__':
  main()
