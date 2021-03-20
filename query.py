import json


def gen_key_count(index):
    keys = sorted([k for k in index if k != "COUNT"], key=lambda k: index[k]["COUNT"], reverse=True)

    for k in keys:
        yield k, index[k]["COUNT"]


def truncate_values(key_counts):
    total = 0

    for k, c in key_counts:
        if "VALUE-" in k and total > 5:
            break

        total += 1
        yield k, c


def print_key_count(index, double=False):
    for key, count in gen_key_count(index):
        print(f"{key} : {count}")

        if double:
            for key2, count2 in truncate_values(gen_key_count(index[key])):
                print(f"\t{key2} : {count2}")



if __name__ == "__main__":
    with open("kube_yaml_index.dat") as f:
        index = json.load(f)

    stack = []

    while True:
        level = len(stack) + 1

        print("Level {}".format(level))
        print("-------------------")

        if level == 1:
            print("All Kinds ->\n")
            print_key_count(index)
        else:
            print("{} ->\n".format(' -> '.join(p[1] for p in stack)))
            print_key_count(index, double=True)

        print("\n")

        while True:
            key = input("key to visit (0 to go back): ")
            print()

            if key == '0' and level > 1:
                index, _ = stack.pop()
                break
            elif key in index:
                stack.append((index, key))
                index = index[key]
                break
            else:
                print("invalid input\n")
