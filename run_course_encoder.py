"""Run the course's LLM-Rec-inspired paraphrase encoder unchanged, on this hardware.

The only difference from ``python far-trans-llm/encoder.py`` is the backend: the
course runtime always loads bfloat16 on CUDA, which a Colab T4 (compute capability
7.5) does not support natively. Here the same model, prompt, greedy decoding and
160-token budget run through attribute_encoder.Generator, which picks float16 on
such GPUs. Same arguments as encoder.py plus --course-dir and --dtype.
"""
import sys
import time

import attribute_encoder as ae


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    course_dir = ae.course_dir_from_argv(argv)
    dtype = 'auto'
    clean = []
    skip = False
    for k, arg in enumerate(argv):  # strip our own flags before encoder.py parses argv
        if skip:
            skip = False
            continue
        if arg in ('--course-dir', '--dtype'):
            if arg == '--dtype':
                dtype = argv[k + 1]
            skip = True
            continue
        clean.append(arg)
    sys.path.insert(0, str(course_dir / 'far-trans-llm'))
    import encoder
    encoder.LocalGenerator = lambda model, revision, device, allow: ae.Generator(
        model, revision, device, dtype, allow)
    started = time.perf_counter()
    sys.argv = ['encoder.py'] + clean
    encoder.main()
    print(f'end_to_end_seconds={time.perf_counter() - started:.1f}')


if __name__ == '__main__':
    main()
