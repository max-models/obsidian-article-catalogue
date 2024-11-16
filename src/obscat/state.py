import yaml
import os
import argparse


def create_state_file(bib_file_path, article_folder_path, output_path=None):
    """
    Creates a state.yml file with paths to a bibliography file and an article folder.

    Parameters:
        bib_file_path (str): Path to the bibliography file (.bib).
        article_folder_path (str): Path to the folder containing articles.
        output_path (str): Path where the state.yml file will be saved.
                           Default is the library path where this script is located.
    """
    # Set default output path to the library path if not provided
    if output_path is None:
        libpath = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(libpath, "state.yml")

    # Dictionary to store paths
    # state_data = {
    #     "bib_file_path": bib_file_path,
    #     "article_folder_path": article_folder_path
    # }
    state_data = load_state_file(input_path=output_path)

    if bib_file_path:
        state_data['bib_file_path'] = bib_file_path
    if article_folder_path:
        state_data['article_folder_path'] = article_folder_path
    print(bib_file_path, article_folder_path)

    # Write the dictionary to a YAML file
    with open(output_path, "w") as file:
        yaml.dump(state_data, file)

    print(f"state.yml file created at {output_path} with the specified paths.")


def load_state_file(input_path=None):
    """
    Loads the state.yml file and returns the paths as a dictionary.

    Parameters:
        input_path (str): Path to the state.yml file. Default is the library path.

    Returns:
        dict: A dictionary with 'bib_file_path' and 'article_folder_path' if found; otherwise, None.
    """
    # Set default input path to the library path if not provided
    if input_path is None:
        libpath = os.path.dirname(os.path.abspath(__file__))
        input_path = os.path.join(libpath, "state.yml")

    if not os.path.exists(input_path):
        state_data = {"bib_file_path": None, "article_folder_path": None}
        return state_data

    # Read the YAML file and return the data
    with open(input_path, "r") as file:
        state_data = yaml.safe_load(file)

    # Ensure the necessary keys are present
    if "bib_file_path" in state_data and "article_folder_path" in state_data:
        print("State file loaded successfully.")
        return state_data
    else:
        print("Error: State file is missing required keys.")
        return None


def main():
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description="Create a state.yml file with paths to bibliography and article folders."
    )
    parser.add_argument(
        "--bib",
        "--bibfile",
        "-b",
        dest="bib_file_path",
        required=False,
        type=str,
        help="Path to the bibliography file (.bib)",
    )
    parser.add_argument(
        "--articles",
        "--articles-dir",
        "-a",
        dest="article_folder_path",
        required=False,
        type=str,
        help="Path to the folder containing articles",
    )
    parser.add_argument(
        "--state-dir",
        type=str,
        default=None,
        help="Path to save state.yml (default is library path)",
    )

    # Parse arguments
    args = parser.parse_args()

    # Create the state file with provided arguments
    create_state_file(args.bib_file_path, args.article_folder_path, args.state_dir)


if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
