def chunk_list(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

print( i for i in chunk_list({1,2,3,4,5,6},2))