#!/usr/bin/env python
""" This "parallel retriever" takes as input a "file manifest" and 
   "retrieval order" for a remotely available BagIt package, and 
    launches a specified number of parallel instances of an appropriate
    retriever tool (rsync, wget) in order to retrieve the contents of
    the package.  It produces a BagIt package as output. If not supplied,
    the name of the package will default to the current timestamp (seconds 
    since Dec 31 1969).
    
    rsync and wget must be available in the $PATH. 

    If an rsync password is necessary, it must be supplied via the environment,
    as in:
      RSYNC_PASSWORD=pass ./parallelretriever.py -m manifest-md5.txt -r fetch.txt 

    Run with '-h' for documentation.
"""

import os, sys, shutil, time
from optparse import OptionParser

def generate_package_identifier():
    """Assume no more than one of these packages per second, and 
       use MIME-encoded seconds-since-epoch."""
    return str(int(time.time()))


def retrieve_package(options):
    """Fork the desired number of retriever processes to 
       work on getting the files"""
    package_directory = os.path.join(options.destination_path,
                                     options.package_identifier)
    if not os.path.isdir(package_directory):
        os.mkdir(package_directory)

    shutil.copy(options.file_manifest,   package_directory)
    shutil.copy(options.retrieval_order, package_directory)
                    
    # distribute the contents of the retrieval order file into 
    # num_processes buckets, round-robin-like.
    retrieval_orders = tuple([ [] for i in range(options.num_processes) ])
    counter = 0
    for line in file(options.retrieval_order).readlines():
        retrieval_item = tuple(line.strip().split())
        bucket_number  = counter % options.num_processes
        retrieval_orders[bucket_number].append(retrieval_item)
        counter = counter + 1

    logfile = file(os.path.join(package_directory, "retrieval.log"), "w")
    pids = []
    for i in range(options.num_processes):
        pid = os.fork()
        if pid:
            pids.append(pid)
        else:
            print "working on %d items in list %d" % (
                   len(retrieval_orders[i]), i)
            for items in retrieval_orders[i]:
                # tolerate older syntax for fetch files, with two tokens
                if len(items) == 2: 
                    url, filename = items
                else: # bagit spec requires three items in fetch.txt
                    url, filesize, filename = items
                filename = os.path.join(package_directory, filename)
                try:
                    os.makedirs(os.path.dirname(filename))
                except OSError:
                    # it's OK if the directories are already there
                    pass
                if url.startswith('rsync'):
                    ret = os.spawnlp(os.P_WAIT, "rsync", "rsync", "-ar", 
                                     url, filename)
                else: # assume wget can handle all other protocols
                    ret = os.spawnlp(os.P_WAIT, "wget", "wget", "-q", "-O", 
                                     filename, url)
                logfile.write("%s %s %d\n" % (time.asctime(), filename, ret))
            sys.exit(0)
       
    for i in range(options.num_processes):
        pid, exit_status = os.wait()
        print "%d finished with status %d" % (pid, exit_status)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-n", "--number-of-processes", dest="num_processes", 
                      type="int", default=16, 
                      help="number of concurrent retrievers to run")
    parser.add_option("-i", "--package-identifier", dest="package_identifier",
                      help="unique identifier for package (will be auto-generated if not supplied)")
    parser.add_option("-m", "--file-manifest", dest="file_manifest",
                      help="path to the file manifest that defines this package")
    parser.add_option("-r", "--retrieval-order", dest="retrieval_order",
                      help="path to the retrieval order (fetch.txt) for this package")
    parser.add_option("-d", "--destination-path", dest="destination_path",
                      help="path in which to create the package")
    options, args = parser.parse_args()

    if options.file_manifest is None:
        parser.error("Supply a file manifest with -m.")

    if options.retrieval_order is None:
        parser.error("Supply a retrieval order with -r.")

    if options.package_identifier is None:
        options.package_identifier = generate_package_identifier()

    if options.destination_path is None:
        options.destination_path = os.getcwd()

    retrieve_package(options)

