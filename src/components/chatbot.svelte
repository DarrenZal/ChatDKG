<script lang="ts">
  import { writable } from 'svelte/store';
  import axios from 'axios';

  const messages = writable([]);
  let newMessage = '';
  let isLoading = writable(false); // To track loading state

  async function sendMessage() {
    if (newMessage.trim() !== '') {
      isLoading.set(true);
      try {
        const response = await axios.post('http://66.42.65.103:5000/generate_query', { question: newMessage });
        const sparqlQuery = response.data.sparql_query;
        messages.update(m => [...m, `Query: ${sparqlQuery}`]);
      } catch (error) {
        console.error("Error generating query:", error);
        messages.update(m => [...m, `Error: Could not generate query.`]); // Show error in chat
      } finally {
        isLoading.set(false);
      }
      newMessage = '';
    }
  }

  function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }
</script>

<section class="chat-container">
  <div class="messages">
    {#each $messages as message}
      <div class="message">{message}</div>
    {/each}
  </div>
  <div class="input-container">
    <textarea
      placeholder="Type a message..."
      bind:value={newMessage}
      on:keydown={handleKeydown}
      rows="3"
      disabled={$isLoading} // Disable input while loading
    ></textarea>
    <button on:click={sendMessage} disabled={$isLoading}>Send</button>
    {#if $isLoading}
      <div class="loading">Loading...</div> <!-- Loading indicator -->
    {/if}
  </div>
</section>

<style>
  .chat-container {
    /* Your styles for the chat container */
  }
  .messages {
    /* Styles for the messages container */
  }
  .message {
    /* Styles for individual messages */
  }
  .input-container {
    /* Styles for the input area */
    display: flex;
    align-items: center;
  }
  .input-container textarea {
    width: 80%; /* Adjust as needed */
    margin-right: 10px;
    font-size: 16px; /* Larger font size */
    padding: 10px;
  }
  .input-container button {
    width: 15%; /* Adjust as needed */
    height: 50px; /* Larger height */
    font-size: 16px; /* Larger font size */
    padding: 5px 10px;
  }
</style>
