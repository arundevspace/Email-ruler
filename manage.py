#!/usr/bin/env python3
import argparse
from data.data_manager import DBManager


def cmd_reset(args):
    db = DBManager()
    if args.all:
        confirm = input("Reset 'processed' for ALL emails? This cannot be undone. (y/N): ")
        if confirm.lower() != 'y':
            print('Canceled')
            return
        db.reset_all_processed()
        print('All emails marked unprocessed.')
    elif args.id:
        db.reset_processed(args.id)
        print(f"Email {args.id} marked unprocessed.")
    elif args.older_than is not None:
        db.reset_processed_older_than(args.older_than)
        print(f"Emails older than {args.older_than} days marked unprocessed.")
    else:
        print('No action specified. Use --all, --id, or --older-than')


def main():
    p = argparse.ArgumentParser(description='Manage email DB flags')
    sub = p.add_subparsers(dest='cmd')

    reset = sub.add_parser('reset-processed', help="Reset processed flags")
    reset.add_argument('--all', action='store_true', help='Reset processed for all emails')
    reset.add_argument('--id', type=str, help='Reset processed for a specific email id')
    reset.add_argument('--older-than', type=int, help='Reset processed for emails older than DAYS')

    args = p.parse_args()

    if args.cmd == 'reset-processed':
        cmd_reset(args)
    else:
        p.print_help()


if __name__ == '__main__':
    main()
